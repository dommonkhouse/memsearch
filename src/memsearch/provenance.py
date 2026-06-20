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
