from __future__ import annotations

import pytest

from memsearch.config import AuthorityRerankConfig
from memsearch.core import MemSearch, _looks_like_exact_identifier, _prioritize_exact_identifier_matches


def test_looks_like_exact_identifier_matches_issue_sha_branch_and_path() -> None:
    assert _looks_like_exact_identifier("MON-316")
    assert _looks_like_exact_identifier("582d619")
    assert _looks_like_exact_identifier("99961250ce2b2538e69d933597517e8c449bc464")
    assert _looks_like_exact_identifier("dom/mon-316-graphiti-falkordb")
    assert _looks_like_exact_identifier("src/memsearch/core.py")


def test_looks_like_exact_identifier_ignores_normal_queries() -> None:
    assert not _looks_like_exact_identifier("memory transcript sources")
    assert not _looks_like_exact_identifier("relationship recall")


def test_prioritize_exact_identifier_matches_before_semantic_scores() -> None:
    results = [
        {"content": "semantic but wrong", "score": 0.99, "heading": "Other", "source": "old.md", "chunk_hash": "a"},
        {
            "content": "Merge commit 582d619d731990fb0a9e0ce9f7f50c53f759c31f",
            "score": 0.21,
            "heading": "23:45",
            "source": "2026-06-13.md",
            "chunk_hash": "b",
        },
    ]

    reranked = _prioritize_exact_identifier_matches("582d619", results)

    assert reranked[0]["chunk_hash"] == "b"


@pytest.mark.asyncio
async def test_search_widens_exact_identifier_candidates_to_collection_size() -> None:
    class FakeEmbedder:
        model_name = "fake-model"
        dimension = 2

        async def embed(self, texts):
            return [[0.0, 1.0] for _ in texts]

    class FakeStore:
        def __init__(self):
            self.search_top_k = None

        def search(self, query_embedding, *, query_text="", top_k=10, filter_expr=""):
            self.search_top_k = top_k
            return [
                {
                    "content": "semantic but wrong",
                    "score": 0.99,
                    "heading": "Other",
                    "source": "old.md",
                    "chunk_hash": "semantic",
                },
                {
                    "content": "Merge commit 582d619d731990fb0a9e0ce9f7f50c53f759c31f",
                    "score": 0.01,
                    "heading": "Batch evidence",
                    "source": "2026-06-13.md",
                    "chunk_hash": "exact",
                },
            ]

        def count(self):
            return 2000

    store = FakeStore()
    mem = MemSearch.__new__(MemSearch)
    mem._embedder = FakeEmbedder()
    mem._store = store
    mem._reranker_model = ""
    mem._author = ""
    mem._citation_scope = "private"
    mem._stale_after_days = 14
    mem._authority_rerank = AuthorityRerankConfig(enabled=False)

    results = await mem.search("582d619", top_k=1)

    assert results[0]["chunk_hash"] == "exact"
    assert store.search_top_k == 2000
