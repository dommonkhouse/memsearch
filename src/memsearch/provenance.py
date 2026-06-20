# src/memsearch/provenance.py
"""Citation, provenance and authority/recency ranking for search results.

Query-time enrichment layer. Adds provenance (date, age), attribution
(author, scope) and a staleness flag to each result, and re-ranks by source
authority and recency. No Milvus schema dependency — everything is derived
from the result dicts MilvusStore.search() already returns.

Ported/adapted from Simon Scrapes' Agentic OS reranker (scripts/lib/reranker.py),
reworked for testability (injectable `today`) and MemSearch's source layout.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Any

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _source_of(result: dict[str, Any]) -> str:
    return result.get("source", "") or result.get("source_path", "") or result.get("path", "") or ""


def extract_file_date(source: str | None) -> date | None:
    if not source:
        return None
    basename = os.path.basename(source.replace("\\", "/"))
    match = _DATE_RE.search(basename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def days_since(d: date | None, *, today: date) -> int | None:
    if d is None:
        return None
    return max((today - d).days, 0)


def resolve_attribution(result: dict[str, Any], *, author: str, scope: str) -> tuple[str, str]:
    """Return (author, scope). TEAM SEAM: today returns the configured constant
    for every chunk (solo). When MemSearch goes multi-user this is the ONE
    function that changes (read per-chunk stored author/owner here). `result`
    is accepted now (unused) so the team change needs no call-site edits."""
    return author, scope


def enrich(results, *, author, scope, today, stale_after_days):
    enriched = []
    for r in results:
        a, s = resolve_attribution(r, author=author, scope=scope)
        d = extract_file_date(_source_of(r))
        age = days_since(d, today=today)
        enriched.append(
            {
                **r,
                "author": a,
                "scope": s,
                "date": d.isoformat() if d else None,
                "days_since": age,
                "stale": (age is not None and age > stale_after_days),
            }
        )
    return enriched
