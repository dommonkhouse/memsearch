from __future__ import annotations

from datetime import date

import pytest

from memsearch.config import AuthorityRerankConfig
from memsearch.core import MemSearch


class FakeEmbedder:
    model_name = "fake-model"
    dimension = 2

    async def embed(self, texts):
        return [[0.0, 1.0] for _ in texts]


class FakeStore:
    """Fake MilvusStore that records and RESPECTS top_k.

    Slicing the returned list to top_k is essential: the candidate-window
    test only proves the fetch_k widening if a store that returns only
    top_k rows would hide the fresh row beyond the window.
    """

    def __init__(self, rows):
        self._rows = list(rows)
        self.search_top_k = None

    def search(self, query_embedding, *, query_text="", top_k=10, filter_expr=""):
        self.search_top_k = top_k
        return self._rows[:top_k]

    def count(self):
        return len(self._rows)


def make_fake_memsearch(
    *,
    rows,
    reranker_model="",
    author="Dominic Monkhouse (dominicmonkhouse)",
    citation_scope="private",
    stale_after_days=14,
    authority_enabled=True,
):
    mem = MemSearch.__new__(MemSearch)
    mem._embedder = FakeEmbedder()
    mem._store = FakeStore(rows)
    mem._reranker_model = reranker_model
    mem._author = author
    mem._citation_scope = citation_scope
    mem._stale_after_days = stale_after_days
    mem._authority_rerank = AuthorityRerankConfig(enabled=authority_enabled)
    return mem


@pytest.mark.asyncio
async def test_search_results_carry_citation_fields() -> None:
    rows = [
        {
            "content": "decided the pricing tier",
            "score": 0.9,
            "heading": "Pricing",
            "source": "/x/.memsearch/memory/2026-06-10.md",
            "chunk_hash": "a",
            "start_line": 5,
            "end_line": 7,
        }
    ]
    mem = make_fake_memsearch(rows=rows)

    results = await mem.search("pricing tier", top_k=5, today=date(2026, 6, 19))

    r = results[0]
    assert r["author"] == "Dominic Monkhouse (dominicmonkhouse)"
    assert r["scope"] == "private"
    assert r["date"] == "2026-06-10"
    assert r["days_since"] == 9
    assert r["stale"] is False


@pytest.mark.asyncio
async def test_recent_result_promoted_from_beyond_top_k() -> None:
    # 12 rows; only the last (raw index 11) is freshly dated. With top_k=5 and a
    # store that respects top_k, the fresh row is only reachable if fetch_k was
    # widened (top_k*3 = 15 >= 12). If fetch_k stayed at 5 the fresh row would
    # never enter the candidate set and could not be promoted.
    rows = [
        {
            "content": f"stale row {i}",
            "score": 0.9,
            "source": "/x/.memsearch/memory/2026-01-01.md",
            "chunk_hash": f"old-{i}",
        }
        for i in range(11)
    ]
    rows.append(
        {
            "content": "fresh row",
            "score": 0.9,
            "source": "/x/.memsearch/memory/2026-06-18.md",
            "chunk_hash": "fresh",
        }
    )
    mem = make_fake_memsearch(rows=rows, authority_enabled=True)

    results = await mem.search("anything", top_k=5, today=date(2026, 6, 19))

    contents = [r["content"] for r in results]
    assert "fresh row" in contents
    # widened candidate window: top_k*3 = 15 covers all 12 rows
    assert mem._store.search_top_k == 15


@pytest.mark.asyncio
async def test_exact_identifier_not_demoted_by_recency() -> None:
    # A stale-dated exact-hash match must stay first; the exact-identifier path
    # skips authority/recency rerank entirely.
    rows = [
        {
            "content": "semantic but wrong",
            "score": 0.99,
            "heading": "Other",
            "source": "/x/.memsearch/memory/2026-06-18.md",
            "chunk_hash": "semantic",
        },
        {
            "content": "Merge commit 582d619d731990fb0a9e0ce9f7f50c53f759c31f",
            "score": 0.01,
            "heading": "Batch evidence",
            "source": "/x/.memsearch/memory/2026-01-01.md",
            "chunk_hash": "exact",
        },
    ]
    mem = make_fake_memsearch(rows=rows, authority_enabled=True)

    results = await mem.search("582d619", top_k=5, today=date(2026, 6, 19))

    assert results[0]["chunk_hash"] == "exact"


@pytest.mark.asyncio
async def test_cross_encoder_composes_with_authority(monkeypatch) -> None:
    calls = {}

    def fake_rerank(query, results, *, model_name="", top_k=0):
        calls["ran"] = True
        calls["top_k"] = top_k
        # return input unsliced so authority rerank sees the full window
        return list(results)

    # search() uses a function-local `from .reranker import rerank`, so patch
    # the SOURCE module, not memsearch.core.
    import memsearch.reranker

    monkeypatch.setattr(memsearch.reranker, "rerank", fake_rerank)

    rows = [
        {
            "content": "old",
            "score": 0.9,
            "source": "/x/.memsearch/memory/2026-04-01.md",
            "chunk_hash": "old",
        },
        {
            "content": "new",
            "score": 0.9,
            "source": "/x/.memsearch/memory/2026-06-18.md",
            "chunk_hash": "new",
        },
    ]
    mem = make_fake_memsearch(rows=rows, reranker_model="x", authority_enabled=True)

    results = await mem.search("anything", top_k=5, today=date(2026, 6, 19))

    assert calls.get("ran") is True
    # cross-encoder saw the full candidate window (authority rerank runs after it)
    assert calls["top_k"] == mem._store.search_top_k
    # final order reflects recency: fresher row wins at equal raw score
    assert results[0]["content"] == "new"


def test_init_sets_citation_defaults(monkeypatch) -> None:
    class FakeProviderObj:
        model_name = "fake-model"
        dimension = 2

    def fake_get_provider(*args, **kwargs):
        return FakeProviderObj()

    class FakeMilvusStore:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("memsearch.core.get_provider", fake_get_provider)
    monkeypatch.setattr("memsearch.core.MilvusStore", FakeMilvusStore)

    mem = MemSearch(paths=["/tmp/x"])

    assert mem._author == ""
    assert mem._stale_after_days == 14
    assert mem._authority_rerank.enabled is True
