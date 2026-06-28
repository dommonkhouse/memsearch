from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .gemini_cards import clear_gemini_cards_output, write_gemini_cards
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
from .models import Conversation, SourceFile
from .parsers.gemini import parse_antigravity_source
from .redact import scan_path_for_secrets
from .source_state import SourceSyncState, read_source_state, source_lock, write_source_state

DEFAULT_HOME = Path.home()
DEFAULT_MEMSEARCH_MEMORY_ROOT = Path.home() / "Projects" / ".memsearch" / "memory"
DEFAULT_LINEAR_OUTPUT_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "linear"
DEFAULT_MANUS_CARD_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "manus-cloud" / "manus-api"
DEFAULT_ANTIGRAVITY_CARD_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "antigravity" / "gemini-cli"


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
    created_since: str | None = None,
    updated_since: str | None = None,
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
    explicit_updated_since = updated_since or since
    effective_since = since or updated_since or created_since or state.last_success_at or ""
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
    date_filtered_task_ids = _date_filtered_task_ids(tasks, created_since=created_since, updated_since=explicit_updated_since)
    has_date_filter = created_since is not None or explicit_updated_since is not None
    selected_task_ids = date_filtered_task_ids if has_date_filter else (None if export_all else changed_task_ids)
    if not export_all and not has_date_filter and not state.task_snapshots:
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
    if not export_all and not has_date_filter and not _timestamps_reliable(tasks):
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
            item_count=len(selected_task_ids) if selected_task_ids is not None else len(tasks),
            card_count=0,
            message="date-filtered preview; state will not be updated" if has_date_filter else "state update preview",
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
            limit=None,
            run_id=run_id,
            resume=resume,
            task_ids=selected_task_ids,
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
        if has_date_filter:
            path = state_dir.expanduser() / "manus.json"
            message = f"date-filtered run; state not updated; raw_secret_hits={len(raw_hits)} promoted_tasks={promotion_summary['rendered_task_count']}"
        else:
            next_state = state.record_success(
                machine=machine,
                run_id=run_id,
                since=effective_since,
                item_count=int(export_summary["tasks_converted"]),
                card_count=int(card_summary["task_cards"]),
                proof_ids=sorted(selected_task_ids or snapshots.keys())[:5],
                task_snapshots=snapshots,
            )
            path = write_source_state(state_dir, next_state)
            message = f"raw_secret_hits={len(raw_hits)} promoted_tasks={promotion_summary['rendered_task_count']}"
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
            message=message,
            steps=steps,
            index_command=tuple(index_result.command),
        )


def sync_antigravity(
    *,
    machine: str,
    home: Path = DEFAULT_HOME,
    since: str | None = None,
    output_root: Path = DEFAULT_ANTIGRAVITY_CARD_ROOT,
    state_dir: Path = Path(".local/source-sync-state"),
    dry_run: bool = False,
    index: bool = False,
    collection: str = "memsearch_chunks",
    max_sessions: int | None = None,
) -> SyncSummary:
    state = read_source_state(state_dir, "antigravity")
    effective_since = since or state.last_success_at or ""
    run_id = _run_id("antigravity")
    actual_output_root = Path(".local/source-sync-dry-runs/antigravity") if dry_run else output_root
    card_dir = actual_output_root.expanduser() / run_id / "cards"
    steps = (
        "discover Gemini chat files and Antigravity CLI transcripts",
        "parse changed sessions",
        "render compact cards",
        "scan cards",
        "update state",
        "optional index",
    )

    with source_lock(state_dir, "antigravity"):
        sources = _discover_gemini_chat_sources(home, machine, max_sessions=max_sessions)
        all_conversations = [parse_antigravity_source(source.path, machine=source.machine) for source in sources]
        conversations = all_conversations
        if since:
            cutoff = _parse_timestamp(since)
            conversations = [conversation for conversation in conversations if _conversation_at_or_after(conversation, cutoff)]
        snapshots = _gemini_session_snapshots(conversations)
        changed = [
            conversation
            for conversation in conversations
            if state.task_snapshots.get(str(conversation.source.path)) != snapshots.get(str(conversation.source.path))
        ]
        actual_output_root = actual_output_root.expanduser()
        actual_output_root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=f".{run_id}-", dir=str(actual_output_root)) as temp_dir:
            staging_dir = Path(temp_dir) / "cards"
            write_gemini_cards(changed, staging_dir, machine=machine, force=True)
            staging_hits = scan_path_for_secrets(staging_dir)
            if staging_hits:
                raise RuntimeError(f"Antigravity card scan found {len(staging_hits)} hit(s)")
        card_summary = write_gemini_cards(changed, card_dir, machine=machine, force=True)
        hits = scan_path_for_secrets(card_dir)
        if hits:
            clear_gemini_cards_output(card_dir)
            raise RuntimeError(f"Antigravity card scan found {len(hits)} hit(s)")
        if index:
            index_result = index_markdown_cards(
                card_dir / "memory" / "antigravity" / "gemini_cli",
                collection=collection,
                dry_run=dry_run,
            )
            if index_result.returncode != 0:
                raise RuntimeError(f"Antigravity indexing failed: {index_result.stderr or index_result.stdout}")
            index_command = tuple(index_result.command)
        else:
            index_command = ()
        if not dry_run:
            next_state = state.record_success(
                machine=machine,
                run_id=run_id,
                since=effective_since,
                item_count=len(changed),
                card_count=int(card_summary["card_count"]),
                proof_ids=sorted(conversation.platform_id for conversation in changed if conversation.platform_id)[:5],
                task_snapshots={**state.task_snapshots, **snapshots},
            )
            path = write_source_state(state_dir, next_state)
        else:
            path = state_dir.expanduser() / "antigravity.json"
        return SyncSummary(
            source="antigravity",
            run_id=run_id,
            status="dry_run" if dry_run else "success",
            dry_run=dry_run,
            since=effective_since,
            machine=machine,
            item_count=len(changed),
            card_count=int(card_summary["card_count"]),
            output_dir=str(card_dir),
            state_path=str(path),
            message="state update preview" if dry_run else "state updated",
            steps=steps,
            index_command=index_command,
        )


def _discover_gemini_chat_sources(home: Path, machine: str, max_sessions: int | None = None) -> list[SourceFile]:
    chat_root = home.expanduser() / ".gemini" / "tmp"
    cli_root = home.expanduser() / ".gemini" / "antigravity-cli"
    sources: list[SourceFile] = []
    if chat_root.is_dir():
        sources.extend(
            SourceFile.from_path(path, product="gemini_cli_chat", machine=machine)
            for path in chat_root.glob("*/chats/*.json")
            if path.is_file()
        )
    if cli_root.is_dir():
        sources.extend(
            SourceFile.from_path(path, product="antigravity_cli_transcript", machine=machine)
            for path in cli_root.glob("brain/*/.system_generated/logs/transcript.jsonl")
            if path.is_file()
        )
    newest_first = sorted(sources, key=lambda source: (-source.mtime, str(source.path)))
    if max_sessions is not None:
        newest_first = newest_first[: max(0, max_sessions)]
    return sorted(newest_first, key=lambda source: str(source.path))


def _gemini_session_snapshots(conversations: list[Conversation]) -> dict[str, str]:
    snapshots: dict[str, str] = {}
    for conversation in conversations:
        last_updated = str(conversation.metadata.get("last_updated") or "").strip()
        value = f"{last_updated}|{conversation.source.content_hash}" if last_updated else conversation.source.content_hash
        snapshots[str(conversation.source.path)] = value
    return snapshots


def _conversation_at_or_after(conversation: Conversation, cutoff: datetime) -> bool:
    value = str(conversation.metadata.get("last_updated") or "").strip()
    if value:
        try:
            return _parse_timestamp(value) >= cutoff
        except ValueError:
            return False
    return datetime.fromtimestamp(conversation.source.mtime, timezone.utc) >= cutoff


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


def _date_filtered_task_ids(tasks: list[dict[str, Any]], *, created_since: str | None, updated_since: str | None) -> list[str] | None:
    if created_since is None and updated_since is None:
        return None
    created_cutoff = _parse_timestamp(created_since) if created_since else None
    updated_cutoff = _parse_timestamp(updated_since) if updated_since else None
    selected: list[str] = []
    for task in tasks:
        task_id = str(task.get("id") or "")
        if not task_id:
            continue
        if created_cutoff is not None and not _task_timestamp_at_or_after(task, ("created_at", "createdAt"), created_cutoff):
            continue
        if updated_cutoff is not None and not _task_timestamp_at_or_after(task, ("updated_at", "updatedAt"), updated_cutoff):
            continue
        selected.append(task_id)
    return sorted(selected)


def _task_timestamp_at_or_after(task: dict[str, Any], keys: tuple[str, str], cutoff: datetime) -> bool:
    value = str(task.get(keys[0]) or task.get(keys[1]) or "").strip()
    if not value:
        return False
    try:
        return _parse_timestamp(value) >= cutoff
    except ValueError:
        return False


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("timestamp cannot be empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def summary_json(summary: SyncSummary) -> str:
    return json.dumps(summary.to_json(), indent=2, sort_keys=True)
