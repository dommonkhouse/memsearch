# tests/test_provenance.py
import math
from datetime import date

from memsearch.provenance import (
    authority_multiplier,
    days_since,
    enrich,
    extract_file_date,
    recency_factor,
    rerank_by_authority_recency,
    resolve_attribution,
)


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


WEIGHTS = {".memsearch/memory/": 1.0, "MEMORY.md": 2.0, "imported-chats/": 0.8}


def test_authority_exact_file_beats_directory():
    assert authority_multiplier("/x/bootstrap/MEMORY.md", WEIGHTS) == 2.0


def test_authority_defaults_to_one():
    assert authority_multiplier("/x/random/file.md", WEIGHTS) == 1.0


def test_recency_factor_halves_at_half_life():
    assert abs(recency_factor("/x/2026-06-05.md", half_life=14, today=date(2026, 6, 19)) - math.exp(-1)) < 1e-9


def test_recency_factor_one_for_undated():
    assert recency_factor("/x/MEMORY.md", half_life=14, today=date(2026, 6, 19)) == 1.0


def test_rerank_prefers_recent_at_equal_score():
    out = rerank_by_authority_recency(
        [
            {"source": "/x/memory/2026-04-01.md", "score": 0.9, "content": "old"},
            {"source": "/x/memory/2026-06-18.md", "score": 0.9, "content": "new"},
        ],
        weights={},
        half_life_days=14,
        recency_floor=0.7,
        floor_ratio=0.3,
        today=date(2026, 6, 19),
    )
    assert out[0]["content"] == "new"


def test_rerank_floor_gates_low_scores():
    out = rerank_by_authority_recency(
        [
            {"source": "/x/2026-06-18.md", "score": 1.0, "content": "keep"},
            {"source": "/x/2026-06-18.md", "score": 0.05, "content": "drop"},
        ],
        weights={},
        half_life_days=14,
        recency_floor=0.7,
        floor_ratio=0.3,
        today=date(2026, 6, 19),
    )
    assert [r["content"] for r in out] == ["keep"]


def test_rerank_top_result_always_survives_even_if_alone():
    out = rerank_by_authority_recency(
        [{"source": "/x/2026-01-01.md", "score": 0.001, "content": "only"}],
        weights={},
        half_life_days=14,
        recency_floor=0.7,
        floor_ratio=0.3,
        today=date(2026, 6, 19),
    )
    assert [r["content"] for r in out] == ["only"]


def test_rerank_tolerates_missing_or_bad_score():
    out = rerank_by_authority_recency(
        [
            {"source": "/x/2026-06-18.md", "content": "no score"},
            {"source": "/x/2026-06-18.md", "score": "bad", "content": "bad score"},
        ],
        weights={},
        half_life_days=14,
        recency_floor=0.7,
        floor_ratio=0.3,
        today=date(2026, 6, 19),
    )
    assert len(out) >= 1
