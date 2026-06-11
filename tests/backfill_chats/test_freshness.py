from __future__ import annotations

from pathlib import Path

from memsearch.backfill.freshness import source_freshness_report
from memsearch.backfill.source_state import read_source_state, write_source_state


def test_freshness_report_includes_state_card_counts_and_proof_preview(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    memory_root = tmp_path / "memory"
    (memory_root / "linear" / "test-mac").mkdir(parents=True)
    (memory_root / "linear" / "test-mac" / "2026-06.md").write_text("## Linear issue MON-318\n", encoding="utf-8")
    state = read_source_state(state_dir, "linear").record_success(
        machine="Test Mac",
        run_id="run-1",
        since="2026-06-10T00:00:00Z",
        item_count=1,
        card_count=1,
        proof_ids=["MON-318"],
    )
    write_source_state(state_dir, state)

    report = source_freshness_report(state_dir=state_dir, memory_root=memory_root)
    linear = next(source for source in report["sources"] if source["source"] == "linear")
    manus = next(source for source in report["sources"] if source["source"] == "manus")

    assert linear["state_status"] == "present"
    assert linear["card_count"] == 1
    assert linear["proof_searches"][0]["status"] == "preview"
    assert manus["state_status"] == "missing-state"
