# tests/test_provenance.py
from datetime import date

from memsearch.provenance import days_since, enrich, extract_file_date, resolve_attribution


def test_extract_file_date_from_dated_filename():
    assert extract_file_date("/x/.memsearch/memory/2026-06-19.md") == date(2026, 6, 19)


def test_extract_file_date_none_for_undated():
    assert extract_file_date("/x/.memsearch/memory/MEMORY.md") is None


def test_extract_file_date_invalid_date_returns_none():
    assert extract_file_date("/x/2026-13-45.md") is None


def test_days_since_counts_whole_days():
    assert days_since(date(2026, 6, 10), today=date(2026, 6, 19)) == 9


def test_days_since_none_for_undated():
    assert days_since(None, today=date(2026, 6, 19)) is None


def test_days_since_clamps_future_to_zero():
    assert days_since(date(2026, 6, 25), today=date(2026, 6, 19)) == 0


def test_resolve_attribution_returns_configured_constant():
    r = {"source": "/x/memory/2026-06-10.md", "content": "decided X"}
    assert resolve_attribution(r, author="Dominic Monkhouse (dominicmonkhouse)", scope="private") == (
        "Dominic Monkhouse (dominicmonkhouse)",
        "private",
    )


def test_enrich_adds_citation_fields():
    results = [
        {
            "source": "/x/memory/2026-06-10.md",
            "content": "c",
            "score": 0.9,
            "start_line": 5,
            "end_line": 7,
            "chunk_hash": "abc",
        }
    ]
    out = enrich(
        results,
        author="Dominic Monkhouse (dominicmonkhouse)",
        scope="private",
        today=date(2026, 6, 19),
        stale_after_days=14,
    )
    r = out[0]
    assert r["author"] == "Dominic Monkhouse (dominicmonkhouse)"
    assert r["scope"] == "private" and r["date"] == "2026-06-10"
    assert r["days_since"] == 9 and r["stale"] is False


def test_enrich_flags_stale_beyond_threshold():
    out = enrich(
        [{"source": "/x/memory/2026-05-01.md", "content": "c", "score": 0.9}],
        author="A",
        scope="private",
        today=date(2026, 6, 19),
        stale_after_days=14,
    )
    assert out[0]["stale"] is True


def test_enrich_undated_source_is_not_stale_and_date_none():
    out = enrich(
        [{"source": "/x/MEMORY.md", "content": "c", "score": 0.9}],
        author="A",
        scope="private",
        today=date(2026, 6, 19),
        stale_after_days=14,
    )
    assert out[0]["date"] is None and out[0]["days_since"] is None and out[0]["stale"] is False
