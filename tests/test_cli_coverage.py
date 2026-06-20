from __future__ import annotations

import json

from click.testing import CliRunner

from memsearch import store as store_module
from memsearch.cli import cli

# A mix of dated memory files and an undated bootstrap file.
# Dated days: 2026-04-04, 2026-04-05, 2026-06-19.
# 2026-04-04 -> 2026-04-05 is 1 day apart (within default gap-days=2, not a gap).
# Gap (default gap-days=2): 2026-04-05 -> 2026-06-19 (75 days).
FAKE_SOURCES = {
    "/x/.memsearch/memory/2026-04-04.md",
    "/x/.memsearch/memory/2026-04-05.md",
    "/x/.memsearch/memory/2026-06-19.md",
    "/x/MEMORY.md",
}


def _patch_store(monkeypatch, sources=None) -> None:
    """Neutralise live-Milvus construction; stub indexed_sources()."""
    if sources is None:
        sources = FAKE_SOURCES

    def fake_init(self, *args, **kwargs):
        return None

    monkeypatch.setattr(store_module.MilvusStore, "__init__", fake_init)
    monkeypatch.setattr(store_module.MilvusStore, "close", lambda self: None)
    monkeypatch.setattr(store_module.MilvusStore, "indexed_sources", lambda self: set(sources))


def test_coverage_json_output_reports_span_and_gaps(monkeypatch) -> None:
    _patch_store(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert payload["earliest"] == "2026-04-04"
    assert payload["latest"] == "2026-06-19"
    assert payload["dated_source_count"] == 3
    assert payload["undated_source_count"] == 1
    # Gaps are [start, end, days] for consecutive dated days > gap-days apart.
    assert payload["gaps"] == [["2026-04-05", "2026-06-19", 75]]


def test_coverage_human_output_mentions_span_and_gap(monkeypatch) -> None:
    _patch_store(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["coverage"])

    assert result.exit_code == 0, result.output
    assert "2026-04-04" in result.output
    assert "2026-06-19" in result.output
    assert "1 undated" in result.output
    assert "2026-04-05 → 2026-06-19" in result.output


def test_coverage_gap_days_threshold_suppresses_small_gaps(monkeypatch) -> None:
    # With gap-days=80, the 75-day gap is no longer a gap.
    _patch_store(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "--gap-days", "80", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["gaps"] == []


def test_coverage_handles_no_dated_sources(monkeypatch) -> None:
    _patch_store(monkeypatch, sources={"/x/MEMORY.md", "/x/SOUL.md"})

    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["earliest"] is None
    assert payload["latest"] is None
    assert payload["dated_source_count"] == 0
    assert payload["undated_source_count"] == 2
    assert payload["gaps"] == []
