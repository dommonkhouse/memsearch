from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

from memsearch.backfill import indexing
from memsearch.backfill import source_sync as source_sync_module
from memsearch.backfill.indexing import IndexResult
from memsearch.backfill.linear_api import LinearIssue
from memsearch.backfill.source_state import read_source_state, write_source_state
from memsearch.backfill.source_sync import (
    DEFAULT_ANTIGRAVITY_CARD_ROOT,
    DEFAULT_LINEAR_OUTPUT_ROOT,
    DEFAULT_MANUS_CARD_ROOT,
    DEFAULT_MEMSEARCH_MEMORY_ROOT,
    sync_antigravity,
    sync_linear,
    sync_manus,
)


class FakeLinearClient:
    def __init__(self) -> None:
        self.since_values: list[str] = []

    def updated_issues(self, *, since: str, limit: int | None = None) -> list[LinearIssue]:
        self.since_values.append(since)
        return [
            LinearIssue(
                id="id",
                identifier="MON-318",
                title="Freshness",
                url="https://linear.app/issue/MON-318",
                updated_at="2026-06-11T00:00:00Z",
                state="Todo",
                team="MON",
            )
        ][:limit]


class FakeManusClient:
    def __init__(self, tasks: list[dict]) -> None:
        self.tasks = tasks

    def iter_tasks(self, max_tasks: int | None = None) -> list[dict]:
        return self.tasks[:max_tasks]


def write_gemini_session(
    home: Path,
    *,
    project_hash: str = "project-alpha",
    session_id: str = "session-alpha",
    start_time: str = "2026-06-27T07:57:35.868Z",
    last_updated: str | None = "2026-06-27T07:58:46.926Z",
) -> Path:
    path = home / ".gemini" / "tmp" / project_hash / "chats" / f"{session_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sessionId": session_id,
        "projectHash": project_hash,
        "startTime": start_time,
        "kind": "main",
        "messages": [
            {"id": f"{session_id}-user", "type": "user", "timestamp": start_time, "content": f"Do {session_id}"},
            {
                "id": f"{session_id}-assistant",
                "type": "gemini",
                "timestamp": "2026-06-27T07:58:46.000Z",
                "content": f"Done {session_id}",
            },
        ],
    }
    if last_updated is not None:
        payload["lastUpdated"] = last_updated
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_antigravity_cli_transcript(home: Path, *, session_id: str = "cli-session") -> Path:
    path = home / ".gemini" / "antigravity-cli" / "brain" / session_id / ".system_generated" / "logs" / "transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "created_at": "2026-06-27T09:00:00Z",
            "content": "<USER_REQUEST>\nUse Antigravity CLI memory.\n</USER_REQUEST>",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "GENERIC",
            "created_at": "2026-06-27T09:00:05Z",
            "content": "Antigravity CLI memory captured.",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def deterministic_run_ids() -> Iterator[str]:
    index = 0
    while True:
        index += 1
        yield f"antigravity-run-{index}"


def test_linear_sync_dry_run_uses_state_since_and_does_not_update_state(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    output = tmp_path / "linear"
    state = read_source_state(state_dir, "linear").record_success(
        machine="Test Mac",
        run_id="old",
        since="2026-06-09T00:00:00Z",
        item_count=1,
        card_count=1,
    )
    write_source_state(state_dir, state)
    client = FakeLinearClient()

    summary = sync_linear(machine="Test Mac", output_root=output, state_dir=state_dir, dry_run=True, client=client)
    loaded = read_source_state(state_dir, "linear")

    assert client.since_values == [state.last_success_at]
    assert summary.status == "dry_run"
    assert summary.card_count == 1
    assert loaded.last_run_id == "old"


def test_linear_sync_updates_state_when_not_dry_run(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    output = tmp_path / "linear"

    summary = sync_linear(
        machine="Test Mac",
        since="2026-06-10T00:00:00Z",
        output_root=output,
        state_dir=state_dir,
        client=FakeLinearClient(),
    )
    state = read_source_state(state_dir, "linear")

    assert summary.status == "success"
    assert state.last_run_id == summary.run_id
    assert state.proof_ids == ["MON-318"]
    assert json.loads((Path(summary.output_dir) / "card-manifest.json").read_text(encoding="utf-8"))["issue_ids"] == ["MON-318"]


def test_linear_sync_raises_when_index_command_fails(tmp_path: Path, monkeypatch) -> None:
    def failing_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        assert command[:3] == [sys.executable, "-m", "memsearch"]
        assert "--no-prune" in command
        assert command[command.index("--batch-size") + 1] == "4"
        return subprocess.CompletedProcess(command, returncode=2, stdout="", stderr="index failed")

    monkeypatch.setattr(indexing, "_run", failing_runner)

    try:
        sync_linear(
            machine="Test Mac",
            since="2026-06-10T00:00:00Z",
            output_root=tmp_path / "linear",
            state_dir=tmp_path / "state",
            index=True,
            client=FakeLinearClient(),
        )
    except RuntimeError as exc:
        assert "index failed" in str(exc)
    else:
        raise AssertionError("sync_linear should fail when indexing fails")


def test_manus_sync_blocks_without_prior_diff_state_unless_all_is_explicit(tmp_path: Path) -> None:
    client = FakeManusClient([{"id": "task-alpha", "updated_at": "2026-06-11T00:00:00Z"}])

    summary = sync_manus(machine="Test Mac", state_dir=tmp_path / "state", dry_run=True, client=client)

    assert summary.status == "blocked"
    assert "--all" in summary.message


def test_manus_sync_dry_run_reports_changed_tasks_from_prior_state(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state = read_source_state(state_dir, "manus").record_success(
        machine="Test Mac",
        run_id="old",
        since="2026-06-01T00:00:00Z",
        item_count=1,
        card_count=1,
        task_snapshots={"task-alpha": "old"},
    )
    write_source_state(state_dir, state)
    client = FakeManusClient([{"id": "task-alpha", "updated_at": "new"}, {"id": "task-beta", "updated_at": "new"}])

    summary = sync_manus(machine="Test Mac", state_dir=state_dir, dry_run=True, client=client)

    assert summary.status == "dry_run"
    assert summary.item_count == 2
    assert any("export changed tasks only" in step for step in summary.steps)


def test_manus_sync_date_filter_dry_run_without_prior_state(tmp_path: Path) -> None:
    client = FakeManusClient(
        [
            {"id": "task-old", "created_at": "2026-05-01T00:00:00Z", "updated_at": "2026-05-02T00:00:00Z"},
            {"id": "task-new", "created_at": "2026-06-12T00:00:00Z", "updated_at": "2026-06-12T01:00:00Z"},
        ]
    )

    summary = sync_manus(
        machine="Test Mac",
        state_dir=tmp_path / "state",
        dry_run=True,
        updated_since="2026-06-01",
        client=client,
    )

    assert summary.status == "dry_run"
    assert summary.item_count == 1
    assert "date-filtered preview" in summary.message


def test_manus_sync_since_aliases_updated_since(tmp_path: Path) -> None:
    client = FakeManusClient(
        [
            {"id": "task-old", "updated_at": "2026-05-02T00:00:00Z"},
            {"id": "task-new", "updated_at": "2026-06-12T01:00:00Z"},
        ]
    )

    summary = sync_manus(
        machine="Test Mac",
        state_dir=tmp_path / "state",
        dry_run=True,
        since="2026-06-01",
        client=client,
    )

    assert summary.status == "dry_run"
    assert summary.since == "2026-06-01"
    assert summary.item_count == 1


def test_manus_sync_date_filter_exports_selected_tasks_without_updating_state(tmp_path: Path, monkeypatch) -> None:
    captured = {}
    client = FakeManusClient(
        [
            {"id": "task-old", "created_at": "2026-05-01T00:00:00Z", "updated_at": "2026-05-02T00:00:00Z"},
            {"id": "task-new", "created_at": "2026-06-12T00:00:00Z", "updated_at": "2026-06-12T01:00:00Z"},
        ]
    )

    def fake_export(client, output_root, *, machine, limit, run_id, resume, task_ids):
        captured["limit"] = limit
        captured["task_ids"] = task_ids
        raw_run = output_root / run_id
        raw_run.mkdir(parents=True)
        return {"tasks_converted": len(task_ids or [])}

    monkeypatch.setattr(source_sync_module, "export_manus_run", fake_export)
    monkeypatch.setattr(source_sync_module, "verify_manus_run", lambda _raw_run: [])
    monkeypatch.setattr(source_sync_module, "scan_path_for_secrets", lambda _path: [])
    monkeypatch.setattr(source_sync_module, "promote_manus_run", lambda *_args, **_kwargs: {"rendered_task_count": 1})
    monkeypatch.setattr(source_sync_module, "generate_manus_memsearch_cards", lambda *_args, **_kwargs: {"task_cards": 1})
    monkeypatch.setattr(
        source_sync_module,
        "index_markdown_cards",
        lambda path, *, collection, dry_run: IndexResult(["memsearch", "index", str(path)], returncode=0),
    )

    state_dir = tmp_path / "state"
    summary = sync_manus(
        machine="Test Mac",
        state_dir=state_dir,
        output_root=tmp_path / "cards",
        updated_since="2026-06-01",
        client=client,
    )

    assert summary.status == "success"
    assert captured == {"limit": None, "task_ids": ["task-new"]}
    assert "state not updated" in summary.message
    assert not (state_dir / "manus.json").exists()


def test_source_sync_defaults_use_shared_memsearch_memory_root() -> None:
    assert Path.home() / "Projects" / ".memsearch" / "memory" == DEFAULT_MEMSEARCH_MEMORY_ROOT
    assert DEFAULT_LINEAR_OUTPUT_ROOT == DEFAULT_MEMSEARCH_MEMORY_ROOT / "linear"
    assert DEFAULT_MANUS_CARD_ROOT == DEFAULT_MEMSEARCH_MEMORY_ROOT / "manus-cloud" / "manus-api"
    assert DEFAULT_ANTIGRAVITY_CARD_ROOT == DEFAULT_MEMSEARCH_MEMORY_ROOT / "antigravity" / "gemini-cli"


def test_antigravity_sync_dry_run_reports_changed_sessions_without_state_write(tmp_path: Path) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    write_gemini_session(home, session_id="session-alpha")
    write_gemini_session(home, session_id="session-beta")

    summary = sync_antigravity(machine="Test Mac", home=home, state_dir=state_dir, dry_run=True)

    assert summary.status == "dry_run"
    assert summary.item_count == 2
    assert summary.card_count == 2
    assert not (state_dir / "antigravity.json").exists()


def test_antigravity_sync_includes_live_cli_transcripts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    write_antigravity_cli_transcript(home)

    summary = sync_antigravity(machine="Test Mac", home=home, state_dir=state_dir, dry_run=True)
    card = Path(summary.output_dir) / "memory" / "antigravity" / "gemini_cli" / "2026-06.md"
    text = card.read_text(encoding="utf-8")

    assert summary.status == "dry_run"
    assert summary.item_count == 1
    assert "source:antigravity_cli_transcript" in text
    assert "Use Antigravity CLI memory." in text
    assert "Antigravity CLI memory captured." in text


def test_antigravity_sync_writes_cards_scans_and_updates_state(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    output_root = tmp_path / "cards"
    run_ids = deterministic_run_ids()
    monkeypatch.setattr(source_sync_module, "_run_id", lambda _source: next(run_ids))
    write_gemini_session(home, session_id="session-alpha")

    summary = sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=state_dir)
    state = read_source_state(state_dir, "antigravity")
    manifest = json.loads((Path(summary.output_dir) / "card-manifest.json").read_text(encoding="utf-8"))

    assert summary.status == "success"
    assert state.last_run_id == summary.run_id
    assert state.proof_ids == ["session-alpha"]
    assert state.task_snapshots
    assert manifest["session_ids"] == ["session-alpha"]
    assert (Path(summary.output_dir) / "memory" / "antigravity" / "gemini_cli" / "2026-06.md").is_file()


def test_antigravity_sync_skips_unchanged_session_snapshots(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    output_root = tmp_path / "cards"
    run_ids = deterministic_run_ids()
    monkeypatch.setattr(source_sync_module, "_run_id", lambda _source: next(run_ids))
    write_gemini_session(home, session_id="session-alpha")

    first = sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=state_dir)
    second = sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=state_dir)

    assert first.card_count == 1
    assert second.status == "success"
    assert second.card_count == 0
    assert read_source_state(state_dir, "antigravity").task_snapshots


def test_antigravity_sync_since_filters_by_last_updated(tmp_path: Path) -> None:
    home = tmp_path / "home"
    write_gemini_session(home, session_id="old", last_updated="2026-06-25T23:59:59Z")
    write_gemini_session(home, session_id="new", last_updated="2026-06-26T00:00:01Z")

    summary = sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=tmp_path / "cards",
        state_dir=tmp_path / "state",
        since="2026-06-26T00:00:00Z",
        dry_run=True,
    )

    assert summary.item_count == 1
    assert summary.card_count == 1


def test_antigravity_sync_since_preserves_existing_snapshot_state(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    output_root = tmp_path / "cards"
    run_ids = deterministic_run_ids()
    monkeypatch.setattr(source_sync_module, "_run_id", lambda _source: next(run_ids))
    write_gemini_session(home, session_id="old", last_updated="2026-06-25T23:59:59Z")
    write_gemini_session(home, session_id="new", last_updated="2026-06-26T00:00:01Z")
    first = sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=state_dir)

    second = sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=output_root,
        state_dir=state_dir,
        since="2026-06-26T00:00:00Z",
    )
    state = read_source_state(state_dir, "antigravity")

    assert first.card_count == 2
    assert second.card_count == 0
    assert len(state.task_snapshots) == 2


def test_antigravity_sync_first_since_run_does_not_mark_unrendered_old_sessions_synced(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    output_root = tmp_path / "cards"
    run_ids = deterministic_run_ids()
    monkeypatch.setattr(source_sync_module, "_run_id", lambda _source: next(run_ids))
    write_gemini_session(home, session_id="old", last_updated="2026-06-25T23:59:59Z")
    write_gemini_session(home, session_id="new", last_updated="2026-06-26T00:00:01Z")

    first = sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=output_root,
        state_dir=state_dir,
        since="2026-06-26T00:00:00Z",
    )
    second = sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=state_dir)

    assert first.card_count == 1
    assert second.card_count == 1
    assert read_source_state(state_dir, "antigravity").proof_ids == ["old"]


def test_antigravity_sync_since_falls_back_to_file_mtime(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path = write_gemini_session(home, session_id="mtime-session", last_updated=None)
    os.utime(path, (1_782_432_001, 1_782_432_001))

    summary = sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=tmp_path / "cards",
        state_dir=tmp_path / "state",
        since="2026-06-26T00:00:00Z",
        dry_run=True,
    )

    assert summary.item_count == 1
    assert summary.card_count == 1


def test_antigravity_sync_indexes_only_when_requested(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    output_root = tmp_path / "cards"
    calls: list[tuple[Path, bool]] = []
    run_ids = deterministic_run_ids()
    monkeypatch.setattr(source_sync_module, "_run_id", lambda _source: next(run_ids))
    write_gemini_session(home, session_id="session-alpha")

    def fake_index(path: Path, *, collection: str, dry_run: bool) -> IndexResult:
        calls.append((path, dry_run))
        return IndexResult(["memsearch", "index", str(path)], returncode=0)

    monkeypatch.setattr(source_sync_module, "index_markdown_cards", fake_index)
    sync_antigravity(machine="Test Mac", home=home, output_root=output_root, state_dir=tmp_path / "state")
    sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=output_root,
        state_dir=tmp_path / "state-2",
        index=True,
    )

    assert len(calls) == 1
    assert calls[0][0] == output_root / "antigravity-run-2" / "cards" / "memory" / "antigravity" / "gemini_cli"
    assert calls[0][1] is False


def test_antigravity_sync_dry_run_index_does_not_mutate_collection(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    calls: list[bool] = []
    write_gemini_session(home, session_id="session-alpha")

    def fake_index(path: Path, *, collection: str, dry_run: bool) -> IndexResult:
        calls.append(dry_run)
        return IndexResult(["memsearch", "index", str(path)], returncode=0, skipped=dry_run)

    monkeypatch.setattr(source_sync_module, "index_markdown_cards", fake_index)

    summary = sync_antigravity(
        machine="Test Mac",
        home=home,
        output_root=tmp_path / "cards",
        state_dir=tmp_path / "state",
        dry_run=True,
        index=True,
    )

    assert summary.status == "dry_run"
    assert calls == [True]


def test_antigravity_sync_secret_scan_failure_records_no_success_state(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    state_dir = tmp_path / "state"
    write_gemini_session(home, session_id="session-alpha")
    scanned: list[Path] = []

    def fake_scan(path: Path) -> list[object]:
        scanned.append(path)
        return [object()]

    monkeypatch.setattr(source_sync_module, "scan_path_for_secrets", fake_scan)

    try:
        sync_antigravity(machine="Test Mac", home=home, output_root=tmp_path / "cards", state_dir=state_dir)
    except RuntimeError as exc:
        assert "Antigravity card scan found 1 hit(s)" in str(exc)
    else:
        raise AssertionError("sync_antigravity should fail on card secret hits")

    assert scanned
    assert all(path.suffix != ".json" for path in scanned)
    assert not (state_dir / "antigravity.json").exists()
    assert not any((tmp_path / "cards").rglob("*.md"))
    assert not any((tmp_path / "cards").rglob("card-manifest.json"))
