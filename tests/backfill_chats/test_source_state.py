from __future__ import annotations

from pathlib import Path

from memsearch.backfill.source_state import read_source_state, source_lock, write_source_state


def test_source_state_round_trips_and_lock_is_removed(tmp_path: Path) -> None:
    state = read_source_state(tmp_path, "linear").record_success(
        machine="Test Mac",
        run_id="run-1",
        since="2026-06-10T00:00:00Z",
        item_count=2,
        card_count=2,
        proof_ids=["MON-318"],
    )

    path = write_source_state(tmp_path, state)
    with source_lock(tmp_path, "linear") as lock_path:
        assert lock_path.is_file()

    loaded = read_source_state(tmp_path, "linear")
    assert path == tmp_path / "linear.json"
    assert not (tmp_path / "linear.lock").exists()
    assert loaded.last_run_id == "run-1"
    assert loaded.proof_ids == ["MON-318"]


def test_source_lock_replaces_stale_pid_lock(tmp_path: Path) -> None:
    lock = tmp_path / "linear.lock"
    lock.write_text("2026-06-11T00:00:00Z\npid=999999\n", encoding="utf-8")

    with source_lock(tmp_path, "linear") as lock_path:
        assert lock_path == lock
        assert "pid=" in lock.read_text(encoding="utf-8")

    assert not lock.exists()
