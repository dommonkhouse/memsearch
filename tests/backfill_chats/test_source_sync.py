from __future__ import annotations

import json
import subprocess
from pathlib import Path

from memsearch.backfill import indexing
from memsearch.backfill.linear_api import LinearIssue
from memsearch.backfill.source_state import read_source_state, write_source_state
from memsearch.backfill.source_sync import sync_linear, sync_manus


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
        assert "--no-prune" in command
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
