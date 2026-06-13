from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .indexing import index_markdown_cards
from .linear_api import LinearApiClient
from .linear_cards import write_linear_cards, write_linear_export
from .manus_api import (
    ManusApiClient,
    export_manus_run,
    generate_manus_memsearch_cards,
    promote_manus_run,
    verify_manus_run,
)
from .redact import scan_path_for_secrets
from .source_state import SourceSyncState, read_source_state, source_lock, write_source_state

DEFAULT_LINEAR_OUTPUT_ROOT = Path("/Users/dominicmonkhouse/Projects/.memsearch/memory/linear")
DEFAULT_MANUS_CARD_ROOT = Path("/Users/dominicmonkhouse/Projects/.memsearch/memory/manus-cloud/manus-api")


@dataclass(frozen=True)
class SyncSummary:
    source: str
    run_id: str
    status: str
    dry_run: bool
    since: str
    machine: str
    item_count: int = 0
    card_count: int = 0
    output_dir: str = ""
    state_path: str = ""
    message: str = ""
    steps: tuple[str, ...] = ()
    index_command: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "run_id": self.run_id,
            "status": self.status,
            "dry_run": self.dry_run,
            "since": self.since,
            "machine": self.machine,
            "item_count": self.item_count,
            "card_count": self.card_count,
            "output_dir": self.output_dir,
            "state_path": self.state_path,
            "message": self.message,
            "steps": list(self.steps),
            "index_command": list(self.index_command),
        }


def sync_linear(
    *,
    machine: str,
    since: str | None = None,
    output_root: Path = DEFAULT_LINEAR_OUTPUT_ROOT,
    state_dir: Path = Path(".local/source-sync-state"),
    dry_run: bool = False,
    index: bool = False,
    collection: str = "memsearch_chunks",
    max_issues: int | None = None,
    client: LinearApiClient | None = None,
) -> SyncSummary:
    state = read_source_state(state_dir, "linear")
    effective_since = since or state.last_success_at or _default_since(days=1)
    run_id = _run_id("linear")
    actual_output_root = Path(".local/source-sync-dry-runs/linear") if dry_run else output_root
    run_dir = actual_output_root.expanduser() / run_id / "export"
    card_dir = actual_output_root.expanduser() / run_id / "cards"
    client = client or LinearApiClient()

    with source_lock(state_dir, "linear"):
        issues = client.updated_issues(since=effective_since, limit=max_issues)
        export_summary = write_linear_export(run_dir, issues=issues, machine=machine, since=effective_since, run_id=run_id)
        card_summary = write_linear_cards(run_dir, card_dir, machine=machine, force=True)
        hits = scan_path_for_secrets(card_dir)
        if hits:
            raise RuntimeError(f"Linear card secret scan found {len(hits)} hit(s)")
        index_result = index_markdown_cards(
            card_dir / "memory" / "linear",
            collection=collection,
            dry_run=dry_run or not index,
        )
        if index_result.returncode != 0:
            raise RuntimeError(f"Linear indexing failed: {index_result.stderr or index_result.stdout}")
        if not dry_run:
            next_state = state.record_success(
                machine=machine,
                run_id=run_id,
                since=effective_since,
                item_count=int(export_summary["issue_count"]),
                card_count=int(card_summary["issue_cards"]),
                proof_ids=[issue.identifier for issue in issues[:5] if issue.identifier],
            )
            path = write_source_state(state_dir, next_state)
        else:
            path = state_dir.expanduser() / "linear.json"
        return SyncSummary(
            source="linear",
            run_id=run_id,
            status="dry_run" if dry_run else "success",
            dry_run=dry_run,
            since=effective_since,
            machine=machine,
            item_count=len(issues),
            card_count=int(card_summary["issue_cards"]),
            output_dir=str(card_dir),
            state_path=str(path),
            message="state update preview" if dry_run else "state updated",
            steps=("fetch updated Linear issues", "write read-only export", "render cards", "scan cards", "optional index"),
            index_command=tuple(index_result.command),
        )


def sync_manus(
    *,
    machine: str,
    since: str | None = None,
    output_root: Path = DEFAULT_MANUS_CARD_ROOT,
    state_dir: Path = Path(".local/source-sync-state"),
    dry_run: bool = False,
    index: bool = False,
    collection: str = "memsearch_chunks",
    max_tasks: int | None = None,
    export_all: bool = False,
    run_id: str | None = None,
    resume: bool = False,
    client: ManusApiClient | None = None,
) -> SyncSummary:
    state = read_source_state(state_dir, "manus")
    effective_since = since or state.last_success_at or ""
    run_id = run_id or _run_id("manus")
    steps = (
        "estimate or fetch task list",
        "compare task IDs and updated_at values with prior state",
        "export changed tasks only when reliable state exists",
        "verify run",
        "scan raw run",
        "promote sanitised Markdown",
        "scan promoted output",
        "generate cards",
        "scan cards",
        "update state",
        "optional index",
    )

    client = client or ManusApiClient()
    tasks = client.iter_tasks(max_tasks=max_tasks)
    snapshots = _task_snapshots(tasks)
    changed_task_ids = _changed_task_ids(snapshots, state)
    if not export_all and not state.task_snapshots:
        return SyncSummary(
            source="manus",
            run_id=run_id,
            status="blocked",
            dry_run=dry_run,
            since=effective_since,
            machine=machine,
            item_count=len(tasks),
            card_count=0,
            message="No prior Manus diff state exists. Weekly sync will not silently run a full export; rerun with --all.",
            steps=steps,
        )
    if not export_all and not _timestamps_reliable(tasks):
        return SyncSummary(
            source="manus",
            run_id=run_id,
            status="blocked",
            dry_run=dry_run,
            since=effective_since,
            machine=machine,
            item_count=len(tasks),
            card_count=0,
            message="Manus task updated_at values are missing or unreliable. Rerun with --all for an explicit full export.",
            steps=steps,
        )
    if dry_run:
        return SyncSummary(
            source="manus",
            run_id=run_id,
            status="dry_run",
            dry_run=True,
            since=effective_since,
            machine=machine,
            item_count=len(changed_task_ids) if not export_all else len(tasks),
            card_count=0,
            message="state update preview",
            steps=steps,
        )

    with source_lock(state_dir, "manus"):
        raw_root = Path(".local/manus-api-export")
        promoted_root = Path(".local/manus-api-indexable") / run_id
        card_root = output_root.expanduser() / run_id
        export_summary = export_manus_run(
            client,
            raw_root,
            machine=machine,
            limit=None if export_all else len(changed_task_ids),
            run_id=run_id,
            resume=resume,
            task_ids=None if export_all else changed_task_ids,
        )
        raw_run = raw_root / run_id
        errors = verify_manus_run(raw_run)
        if errors:
            raise RuntimeError("Manus run verification failed: " + "; ".join(errors[:5]))
        raw_hits = scan_path_for_secrets(raw_run)
        promotion_summary = promote_manus_run(raw_run, promoted_root, force=True)
        promoted_hits = scan_path_for_secrets(promoted_root)
        if promoted_hits:
            raise RuntimeError(f"promoted Manus scan found {len(promoted_hits)} hit(s)")
        card_summary = generate_manus_memsearch_cards(promoted_root, card_root, force=True)
        card_hits = scan_path_for_secrets(card_root)
        if card_hits:
            raise RuntimeError(f"Manus card scan found {len(card_hits)} hit(s)")
        index_result = index_markdown_cards(card_root / "memory" / "manus_cloud" / "manus_api", collection=collection, dry_run=not index)
        if index_result.returncode != 0:
            raise RuntimeError(f"Manus indexing failed: {index_result.stderr or index_result.stdout}")
        next_state = state.record_success(
            machine=machine,
            run_id=run_id,
            since=effective_since,
            item_count=int(export_summary["tasks_converted"]),
            card_count=int(card_summary["task_cards"]),
            proof_ids=sorted(changed_task_ids or snapshots.keys())[:5],
            task_snapshots=snapshots,
        )
        path = write_source_state(state_dir, next_state)
        return SyncSummary(
            source="manus",
            run_id=run_id,
            status="success",
            dry_run=False,
            since=effective_since,
            machine=machine,
            item_count=int(export_summary["tasks_converted"]),
            card_count=int(card_summary["task_cards"]),
            output_dir=str(card_root),
            state_path=str(path),
            message=f"raw_secret_hits={len(raw_hits)} promoted_tasks={promotion_summary['rendered_task_count']}",
            steps=steps,
            index_command=tuple(index_result.command),
        )


def _default_since(*, days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _run_id(source: str) -> str:
    return f"{source}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _task_snapshots(tasks: list[dict[str, Any]]) -> dict[str, str]:
    return {str(task.get("id")): str(task.get("updated_at") or task.get("updatedAt") or "") for task in tasks if task.get("id")}


def _changed_task_ids(snapshots: dict[str, str], state: SourceSyncState) -> list[str]:
    return sorted(task_id for task_id, updated_at in snapshots.items() if state.task_snapshots.get(task_id) != updated_at)


def _timestamps_reliable(tasks: list[dict[str, Any]]) -> bool:
    return all(str(task.get("updated_at") or task.get("updatedAt") or "").strip() for task in tasks)


def summary_json(summary: SyncSummary) -> str:
    return json.dumps(summary.to_json(), indent=2, sort_keys=True)
