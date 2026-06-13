from __future__ import annotations

from memsearch.core import _looks_like_exact_identifier, _prioritize_exact_identifier_matches


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
