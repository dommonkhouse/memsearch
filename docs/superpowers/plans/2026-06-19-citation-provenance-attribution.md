# Citation, Provenance & Attribution for MemSearch Recall — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every MemSearch recall result carry a trustworthy citation — source path + line range + date + age + "decided by" attribution + a staleness flag — and rank results so the freshest, most authoritative memory wins, porting Simon Scrapes' Agentic OS citation/reranking model into MemSearch's native Python pipeline.

**Architecture:** Add a query-time enrichment + ranking layer (no Milvus schema change, no reindex). A new `provenance` module derives `date`/`days_since` from the source filename, stamps `author`/`scope` via a single `resolve_attribution()` seam (today returns the configured constant "Dominic Monkhouse (dominicmonkhouse)"; in team mode this one function reads per-chunk metadata), applies Simon's authority×recency×floor reranking on the candidate set, and flags stale results. Ranking runs on the full candidate set *before* slicing to `top_k`; enrichment runs *after* slicing (cheap, ~`top_k` rows). The CLI surfaces these fields in JSON and human output; a new `coverage` command backs honest "partial/absent" answers; the recall skill cites them.

**Tech Stack:** Python 3.11+, dataclass config (`tomllib`/`tomli_w`), Milvus (via `MilvusStore`), Click CLI, pytest. Pure-Python ranking maths (no model, no DB round-trip).

---

## Why this shape (key decisions)

1. **No reindex now.** `author` is a constant today (everything is Dom), and `date` is derivable from the source path. Both are computed at query time in result enrichment, so we touch the read path only — not the Milvus schema. A reindex would re-embed the whole corpus to store a constant; deferred to the team phase where author varies per chunk.
2. **Team-forward seam.** All attribution flows through one function, `resolve_attribution(result, ...)`. Today it returns the configured constant for every chunk. The team upgrade changes only this function (read stored per-chunk author/owner) plus adds scope filtering — the output schema, citation format, CLI/JSON and recall skill are already team-shaped.
3. **Authority×recency is complementary to the existing cross-encoder, not redundant.** The cross-encoder (`reranker.py:236` `rerank()`, opt-in, default off) improves *relevance*. The new authority×recency×floor pass applies *freshness + source-authority* weighting and noise-gating. They compose: cross-encoder (if enabled) runs first, then authority×recency re-weights its output. `reranker.py` is untouched.
4. **Exact-identifier queries skip authority/recency rerank.** `core.py:236-248` special-cases identifier lookups and widens `fetch_k` to up to `count()`. Recency-weighting an exact hash/path lookup could bury the exact hit, so those queries keep current behaviour (prioritise exact match, no recency rerank).
5. **Ordering (corrected after review):** `store.search` (fetch_k candidates) → optional cross-encoder → **either** exact-identifier prioritise **or** authority/recency rerank (on the full candidate set) → **slice `[:top_k]`** → **`enrich`**. Enrich runs last so the per-row date/author stamping only ever touches ~`top_k` rows, never the widened exact-identifier candidate set (which can be thousands). `search()` gains an injectable `today` param so staleness/recency are deterministic in tests.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `src/memsearch/provenance.py` | Date extraction, age, attribution resolver, enrichment, authority×recency×floor rerank | **Create** |
| `src/memsearch/config.py` | `CitationConfig` + `AuthorityRerankConfig`; `_FLOAT_FIELDS` coercion | Modify (`29-37`, `76-79`, `178-204`, `514-524`) |
| `src/memsearch/core.py` | `__init__` params; `search()` ordering + `today` param + enrich/rerank wiring | Modify (`51-85`, `205-249`) |
| `src/memsearch/cli.py` | `_cfg_to_memsearch_kwargs` carries citation kwargs; citation line in human output; `coverage` command | Modify (`90-104`, `404-420`) + add command |
| `~/.claude/skills/memory-recall/SKILL.md` | Cite author/date/age/stale; use `coverage` (machine config — not a repo commit) | Modify (deployed) |
| `plugins/claude-code/skills/memory-recall/SKILL.md` | Add the citation/honesty contract (currently bare, 50 lines) | Modify (repo) |
| `tests/test_provenance.py` | Unit tests for all provenance functions | **Create** |
| `tests/test_core_provenance.py` | Integration via a `make_fake_memsearch` helper (modelled on `tests/test_core_exact_identifiers.py:40-78`) + one real-`__init__` defaults test | **Create** |
| `tests/test_cli_coverage.py` | `coverage` command output | **Create** |

---

## Not included in this version (Deferred Decisions)

- **Team scoping / row-level access control.** Considered: per-contributor `author`+`scope` stored per chunk, every query filtered by who's asking (the GBrain model — the part Simon admits in the video he has *not* shipped). Deferred because Dom confirmed all decisions are his and only his until we flip to team. Worth adding when a second contributor exists. Convergence: extends the `resolve_attribution()` seam + a stored `author`/`scope` field (schema add + one reindex) + a scope filter in `MilvusStore.search()`. This plan builds the seam so that work is additive.
- **Storing `author`/`date` per chunk in Milvus.** Deferred (reindex cost); only needed when author varies.
- **LLM synthesis layer.** Neither system has one; both let the agent write the cited answer from ranked chunks. Not building it.
- **Cross-encoder on by default.** Tracked under `docs/superpowers/plans/2026-06-12-memsearch-reranking-benchmark.md` (MON-322). Untouched here.
- **Phase 3 (`coverage`) — reviewer flagged as cuttable.** The plan-document-reviewer recommended splitting Phase 3 into a follow-up (it's a second CLI surface). Kept here because honest partial/absent answers are part of Simon's citation model and `store.indexed_sources()` already exists (`store.py:241`), so it's low-cost. **Flagged for Dom's call** — see Review status.

---

## Phase 1 — Provenance enrichment (date + age + author + stale)

*Unblocks the headline "citations" behaviour: every result carries source:line:date + "decided by" + age.*

### Task 1: Date extraction and age helpers

**Files:**
- Create: `src/memsearch/provenance.py`
- Test: `tests/test_provenance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_provenance.py
import math
from datetime import date
from memsearch.provenance import extract_file_date, days_since

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
```

- [ ] **Step 2: Run test to verify it fails** — `uv run pytest tests/test_provenance.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation** (port of `agentic-os/scripts/lib/reranker.py:82-93`, with injectable `today`)

```python
# src/memsearch/provenance.py
"""Citation, provenance and authority/recency ranking for search results.

Query-time enrichment layer. Adds source provenance (date, age), attribution
(author, scope) and a staleness flag to each result, and re-ranks results by
source authority and recency. No Milvus schema dependency — everything is
derived from the result dicts MilvusStore.search() already returns.

Ported and adapted from Simon Scrapes' Agentic OS reranker
(scripts/lib/reranker.py), reworked for testability (injectable `today`) and
MemSearch's source layout.
"""

from __future__ import annotations

import math
import os
import re
from datetime import date, datetime
from typing import Any

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _source_of(result: dict[str, Any]) -> str:
    """Source path for a result. MemSearch emits `source`; keep `source_path`/
    `path` fallbacks so a non-Milvus producer's results enrich/rank identically."""
    return result.get("source", "") or result.get("source_path", "") or result.get("path", "") or ""


def extract_file_date(source: str | None) -> date | None:
    """Extract a YYYY-MM-DD date from a source filename, else None."""
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
    """Whole days between *d* and *today*; never negative; None if undated."""
    if d is None:
        return None
    return max((today - d).days, 0)
```

- [ ] **Step 4: Run test to verify it passes** — `uv run pytest tests/test_provenance.py -v` → PASS.

- [ ] **Step 5: Full gate** — `uv run pytest && uv run ruff check src tests && uv run ruff format --check src tests`. Expected: zero findings.

- [ ] **Step 6: Commit** — `git add src/memsearch/provenance.py tests/test_provenance.py && git commit -m "feat(provenance): date extraction + age helpers (MON-XXX)"`

### Task 2: Attribution resolver (team seam) + result enrichment

**Files:**
- Modify: `src/memsearch/provenance.py`
- Test: `tests/test_provenance.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from memsearch.provenance import resolve_attribution, enrich

def test_resolve_attribution_returns_configured_constant():
    r = {"source": "/x/memory/2026-06-10.md", "content": "decided X"}
    assert resolve_attribution(r, author="Dominic Monkhouse (dominicmonkhouse)", scope="private") \
        == ("Dominic Monkhouse (dominicmonkhouse)", "private")

def test_enrich_adds_citation_fields():
    results = [{"source": "/x/memory/2026-06-10.md", "content": "c", "score": 0.9,
                "start_line": 5, "end_line": 7, "chunk_hash": "abc"}]
    out = enrich(results, author="Dominic Monkhouse (dominicmonkhouse)", scope="private",
                 today=date(2026, 6, 19), stale_after_days=14)
    r = out[0]
    assert r["author"] == "Dominic Monkhouse (dominicmonkhouse)"
    assert r["scope"] == "private"
    assert r["date"] == "2026-06-10"
    assert r["days_since"] == 9
    assert r["stale"] is False

def test_enrich_flags_stale_beyond_threshold():
    results = [{"source": "/x/memory/2026-05-01.md", "content": "c", "score": 0.9}]
    out = enrich(results, author="A", scope="private", today=date(2026, 6, 19), stale_after_days=14)
    assert out[0]["stale"] is True

def test_enrich_undated_source_is_not_stale_and_date_none():
    results = [{"source": "/x/MEMORY.md", "content": "c", "score": 0.9}]
    out = enrich(results, author="A", scope="private", today=date(2026, 6, 19), stale_after_days=14)
    assert out[0]["date"] is None
    assert out[0]["days_since"] is None
    assert out[0]["stale"] is False  # undated → cannot assert staleness
```

- [ ] **Step 2: Run test to verify it fails** — FAIL (functions missing).

- [ ] **Step 3: Write minimal implementation**

```python
def resolve_attribution(result: dict[str, Any], *, author: str, scope: str) -> tuple[str, str]:
    """Return (author, scope) for a result.

    TEAM SEAM: today this returns the configured constant for every chunk
    (solo mode — all memories are Dom's). When MemSearch goes multi-user this
    is the ONE function that changes: read per-chunk stored author/owner
    metadata here instead of the config constant. `result` is accepted now
    (unused) so the team change needs no signature edit at call sites.
    """
    return author, scope


def enrich(
    results: list[dict[str, Any]],
    *,
    author: str,
    scope: str,
    today: date,
    stale_after_days: int,
) -> list[dict[str, Any]]:
    """Attach citation fields (author, scope, date, days_since, stale)."""
    enriched: list[dict[str, Any]] = []
    for r in results:
        a, s = resolve_attribution(r, author=author, scope=scope)
        d = extract_file_date(_source_of(r))
        age = days_since(d, today=today)
        enriched.append({
            **r,
            "author": a,
            "scope": s,
            "date": d.isoformat() if d else None,
            "days_since": age,
            "stale": (age is not None and age > stale_after_days),
        })
    return enriched
```

- [ ] **Step 4: Run test to verify it passes** — PASS.
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(provenance): attribution resolver seam + result enrichment (MON-XXX)"`

### Task 3: Config — `CitationConfig`

**Files:**
- Modify: `src/memsearch/config.py` (dataclass near `76-79`; register in `MemSearchConfig` `178-190` and `_SECTION_CLASSES` `193-204`; add `stale_after_days` to `_INT_FIELDS` `29-36`)
- Test: `tests/test_config.py`

**Note (verified):** adding a flat-field dataclass to `MemSearchConfig` + `_SECTION_CLASSES` is the complete touch-point set — `_dict_to_config` (`354-370`) reconstructs via the generic `cls(**filtered)`, which handles scalar and plain `dict` fields. No `_dict_to_config` special-case is needed (unlike `_dict_to_llm_config`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py (append)
from memsearch.config import resolve_config, MemSearchConfig

def test_citation_defaults():
    cfg = MemSearchConfig()
    assert cfg.citation.author == ""
    assert cfg.citation.scope == "private"
    assert cfg.citation.stale_after_days == 14

def test_citation_config_from_toml(tmp_path, monkeypatch):
    p = tmp_path / ".memsearch.toml"
    p.write_text('[citation]\nauthor = "Dominic Monkhouse (dominicmonkhouse)"\nstale_after_days = 30\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve_config()
    assert cfg.citation.author == "Dominic Monkhouse (dominicmonkhouse)"
    assert cfg.citation.stale_after_days == 30
```

- [ ] **Step 2: Run test to verify it fails** — FAIL (`citation` attr missing).

- [ ] **Step 3: Write minimal implementation**

```python
# config.py — new dataclass near RerankerConfig (line ~76)
@dataclass
class CitationConfig:
    author: str = ""          # "" => CLI falls back to a generic owner label
    scope: str = "private"    # team seam: system/team/client/private
    stale_after_days: int = 14
```
Add `citation: CitationConfig = field(default_factory=CitationConfig)` to `MemSearchConfig`; add `"citation": CitationConfig` to `_SECTION_CLASSES`; add `"stale_after_days"` to `_INT_FIELDS`.

- [ ] **Step 4: Run test to verify it passes** — PASS.
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(config): CitationConfig (author/scope/stale) (MON-XXX)"`

### Task 4: Wire enrichment into `MemSearch.search()` (with injectable `today`)

**Files:**
- Modify: `src/memsearch/core.py` (`__init__` `51-85`; `search()` `205-249`)
- Create: `tests/test_core_provenance.py`

**Fixture note (verified):** there is NO `fake_memsearch_factory` in the repo and `tests/test_core.py` uses a *real* `MemSearch` gated on `OPENAI_API_KEY`. Build a `make_fake_memsearch(...)` helper in the new test file, modelled exactly on `tests/test_core_exact_identifiers.py:40-78` (inline `FakeEmbedder`/`FakeStore`, `MemSearch.__new__`). Because `__new__` bypasses `__init__`, the helper MUST set every attribute `search()` reads: `_embedder`, `_store`, `_reranker_model`, **and the new** `_author`, `_citation_scope`, `_stale_after_days`, `_authority_rerank`.

- [ ] **Step 1: Write the failing tests** (fake store + a real-`__init__` defaults test so `__init__` additions get coverage)

```python
# tests/test_core_provenance.py
import asyncio
from datetime import date
from memsearch.core import MemSearch
from memsearch.config import AuthorityRerankConfig

def make_fake_memsearch(stored, *, author="Dominic Monkhouse (dominicmonkhouse)",
                        reranker_model="", authority_enabled=False):
    class FakeEmbedder:
        model_name = "fake-model"; dimension = 2
        async def embed(self, texts): return [[0.0, 1.0] for _ in texts]
    class FakeStore:
        def search(self, qe, *, query_text="", top_k=10, filter_expr=""): return list(stored)
        def count(self): return len(stored)
    mem = MemSearch.__new__(MemSearch)
    mem._embedder = FakeEmbedder(); mem._store = FakeStore(); mem._reranker_model = reranker_model
    mem._author = author; mem._citation_scope = "private"; mem._stale_after_days = 14
    mem._authority_rerank = AuthorityRerankConfig(enabled=authority_enabled)
    return mem

def test_search_results_carry_citation_fields():
    mem = make_fake_memsearch([{"source": "/x/memory/2026-06-10.md", "content": "price 37",
                                "score": 0.9, "start_line": 5, "end_line": 7, "chunk_hash": "h"}])
    res = asyncio.run(mem.search("pricing", top_k=5, today=date(2026, 6, 19)))
    assert res[0]["author"] == "Dominic Monkhouse (dominicmonkhouse)"
    assert res[0]["date"] == "2026-06-10"
    assert res[0]["days_since"] == 9 and res[0]["stale"] is False

def test_init_sets_citation_defaults():
    # Exercise the REAL __init__ (not __new__) with a stubbed store/embedder via monkeypatch
    # of get_provider + MilvusStore is overkill; instead assert the dataclass defaults the
    # __init__ reads. Construct with minimal args and a patched store/embedder.
    # (Implementer: patch memsearch.core.get_provider and MilvusStore to no-op fakes,
    #  then assert mem._author == "" and mem._stale_after_days == 14 and
    #  mem._authority_rerank.enabled is True by default.)
    ...
```

- [ ] **Step 2: Run test to verify it fails** — FAIL (no citation fields / params).

- [ ] **Step 3: Write minimal implementation** — add `__init__` params (defaults keep existing callers working) and rewire `search()`:

```python
# __init__ additions:
        author: str = "",
        citation_scope: str = "private",
        stale_after_days: int = 14,
        authority_rerank: "AuthorityRerankConfig | None" = None,
# stored on self:
        self._author = author
        self._citation_scope = citation_scope
        self._stale_after_days = stale_after_days
        from .config import AuthorityRerankConfig
        self._authority_rerank = authority_rerank or AuthorityRerankConfig()

# search() signature gains: today: "date | None" = None
# at the END of search(), replacing the current `return results[:top_k]` block:
        from datetime import date as _date
        from .provenance import enrich
        today = today or _date.today()
        # (authority/recency rerank inserted in Task 8 — for now just slice + enrich)
        results = results[:top_k]
        return enrich(results, author=self._author, scope=self._citation_scope,
                      today=today, stale_after_days=self._stale_after_days)
```
(`today` is injectable so staleness/recency are deterministic in tests; prod passes `None` → `date.today()`.)

- [ ] **Step 4: Run test to verify it passes** — PASS.
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(core): enrich search results with citation fields (MON-XXX)"`

### Task 5: Surface citation fields in the CLI

**Files:**
- Modify: `src/memsearch/cli.py` — **`_cfg_to_memsearch_kwargs` (`90-104`)** so ALL call sites (search `369`, compact `1256`, index `297`, graph_eval `559`) construct `MemSearch` with citation kwargs consistently; human-output loop (`404-420`) prints a citation line. JSON path (`394-401`) needs no change — enriched fields ride in each result dict already.
- Test: `tests/test_cli_search_citation.py`

- [ ] **Step 1: Write the failing test** — `CliRunner` + monkeypatched `MilvusStore` (pattern from `tests/test_cli_error_handling.py`) and a config whose `[citation] author` is set to the full string. Assert human output contains `decided by Dominic Monkhouse` and `2026-06-10`; assert `--json-output` includes `"author"` and `"days_since"`.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — add to the dict returned by `_cfg_to_memsearch_kwargs`:
```python
        "author": cfg.citation.author,
        "citation_scope": cfg.citation.scope,
        "stale_after_days": cfg.citation.stale_after_days,
        "authority_rerank": cfg.authority_rerank,
```
In the human-output loop add (using `cfg.citation.author or "the owner"` fallback handled in CLI display, not in enrich):
```python
            author_disp = r.get("author") or "the owner"
            cite = f"  decided by {author_disp}"
            if r.get("date"):
                cite += f" · {r['date']} ({r['days_since']}d ago)"
            if r.get("stale"):
                cite += "  ⚠ stale"
            click.echo(cite)
```
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(cli): show decided-by/date/age citation in search output (MON-XXX)"`

---

## Phase 2 — Authority × recency × floor reranking (on by default)

*Makes the freshest, most authoritative memory rank first, so the cited answer is the current decision, not a stale one.*

### Task 6: Port the authority/recency/floor reranker

**Files:**
- Modify: `src/memsearch/provenance.py`
- Test: `tests/test_provenance.py`

- [ ] **Step 1: Write the failing test**

```python
from memsearch.provenance import authority_multiplier, recency_factor, rerank_by_authority_recency

DEFAULT_WEIGHTS = {".memsearch/memory/": 1.0, "MEMORY.md": 2.0, "imported-chats/": 0.8}

def test_authority_exact_file_beats_directory():
    assert authority_multiplier("/x/bootstrap/MEMORY.md", DEFAULT_WEIGHTS) == 2.0

def test_authority_defaults_to_one():
    assert authority_multiplier("/x/random/file.md", DEFAULT_WEIGHTS) == 1.0

def test_recency_factor_halves_at_half_life():
    f = recency_factor("/x/2026-06-05.md", half_life=14, today=date(2026, 6, 19))
    assert abs(f - math.exp(-14/14)) < 1e-9

def test_recency_factor_one_for_undated():
    assert recency_factor("/x/MEMORY.md", half_life=14, today=date(2026, 6, 19)) == 1.0

def test_rerank_prefers_recent_over_stale_at_equal_score():
    results = [
        {"source": "/x/memory/2026-04-01.md", "score": 0.9, "content": "old"},
        {"source": "/x/memory/2026-06-18.md", "score": 0.9, "content": "new"},
    ]
    out = rerank_by_authority_recency(results, weights={}, half_life_days=14,
                                      recency_floor=0.7, floor_ratio=0.3, today=date(2026, 6, 19))
    assert out[0]["content"] == "new"

def test_rerank_floor_gates_low_scores():
    results = [{"source": "/x/2026-06-18.md", "score": 1.0, "content": "keep"},
               {"source": "/x/2026-06-18.md", "score": 0.05, "content": "drop"}]
    out = rerank_by_authority_recency(results, weights={}, half_life_days=14,
                                      recency_floor=0.7, floor_ratio=0.3, today=date(2026, 6, 19))
    assert [r["content"] for r in out] == ["keep"]

def test_rerank_top_result_always_survives_even_if_alone():
    results = [{"source": "/x/2026-01-01.md", "score": 0.001, "content": "only"}]
    out = rerank_by_authority_recency(results, weights={}, half_life_days=14,
                                      recency_floor=0.7, floor_ratio=0.3, today=date(2026, 6, 19))
    assert [r["content"] for r in out] == ["only"]  # threshold = top*ratio; top >= threshold

def test_rerank_tolerates_missing_or_bad_score():
    results = [{"source": "/x/2026-06-18.md", "content": "no score"},
               {"source": "/x/2026-06-18.md", "score": "bad", "content": "bad score"}]
    out = rerank_by_authority_recency(results, weights={}, half_life_days=14,
                                      recency_floor=0.7, floor_ratio=0.3, today=date(2026, 6, 19))
    assert len(out) >= 1  # does not raise
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement** — port of `agentic-os/scripts/lib/reranker.py:49-159`, `today` injected, tolerant of malformed scores, top-result-survives invariant preserved:

```python
def authority_multiplier(source: str | None, weights: dict[str, float]) -> float:
    if not source:
        return 1.0
    path = source.replace("\\", "/")
    best_weight, best_len = None, -1
    for key, weight in weights.items():            # exact-file match wins, longest key
        nkey = key.replace("\\", "/")
        if not nkey.endswith("/") and path.endswith(nkey) and len(nkey) > best_len:
            best_len, best_weight = len(nkey), weight
    if best_weight is not None:
        return best_weight
    best_len = -1                                   # directory/prefix match, longest key
    for key, weight in weights.items():
        nkey = key.replace("\\", "/")
        if nkey.endswith("/") and (("/" + nkey) in ("/" + path) or path.startswith(nkey)) and len(nkey) > best_len:
            best_len, best_weight = len(nkey), weight
    return best_weight if best_len >= 0 else 1.0


def recency_factor(source: str | None, *, half_life: float, today: date) -> float:
    d = extract_file_date(source)
    if d is None:
        return 1.0
    age = max((today - d).days, 0)
    return math.exp(-age / half_life)


def rerank_by_authority_recency(
    results: list[dict[str, Any]],
    *,
    weights: dict[str, float],
    half_life_days: float,
    recency_floor: float,
    floor_ratio: float,
    today: date,
) -> list[dict[str, Any]]:
    if not results:
        return results
    scored = []
    for item in results:
        try:
            raw = float(item.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            raw = 0.0
        src = _source_of(item)
        s1 = raw * authority_multiplier(src, weights)
        rf = recency_factor(src, half_life=half_life_days, today=today)
        s2 = s1 * (recency_floor + (1.0 - recency_floor) * rf)
        scored.append({**item, "_s2": s2})
    top = max(x["_s2"] for x in scored)
    threshold = top * floor_ratio
    final = [
        {**{k: v for k, v in it.items() if not k.startswith("_")},
         "final_score": round(it["_s2"], 6), "reranked": True}
        for it in scored if it["_s2"] >= threshold
    ]
    final.sort(key=lambda x: x["final_score"], reverse=True)
    return final
```
(Note: when all scores are 0, `top == 0`, `threshold == 0`, and `0 >= 0` keeps everything — no crash, no empty result.)

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(provenance): authority/recency/floor reranker (MON-XXX)"`

### Task 7: Config — `AuthorityRerankConfig` (with REQUIRED float coercion)

**Files:** Modify `src/memsearch/config.py`. Test `tests/test_config.py`.

**Critical (verified):** `config.py` has only `_INT_FIELDS` (`29-36`) and `_BOOL_FIELDS` (`37`) — there is **no** `_FLOAT_FIELDS` and no `float(` coercion anywhere. This is a REQUIRED fix, not polish: without it, `memsearch config set authority_rerank.floor_ratio 0.4` writes the string `"0.4"`, which reloads as `str`, and `top * floor_ratio` in the reranker raises `TypeError`.

- [ ] **Step 1: Write the failing test** — defaults (`enabled=True`, `half_life_days=14`, `floor_ratio=0.3`, `recency_floor=0.7`, MemSearch-specific `authority_weights`); a TOML override of `half_life_days` + `floor_ratio` (proves float survives load); and `set_config_value("authority_rerank.floor_ratio", "0.4")` round-trips to a `float` 0.4 (proves coercion).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement**

```python
@dataclass
class AuthorityRerankConfig:
    enabled: bool = True
    half_life_days: int = 14
    floor_ratio: float = 0.3
    recency_floor: float = 0.7
    authority_weights: dict[str, float] = field(default_factory=lambda: {
        "MEMORY.md": 2.0, "SOUL.md": 1.5, "USER.md": 1.5,
        "linear/": 1.1, ".memsearch/memory/": 1.0,
        "imported-chats/": 0.8, "transcripts/": 0.8,
    })
```
Register in `MemSearchConfig` + `_SECTION_CLASSES` as `authority_rerank`. Add `half_life_days` to `_INT_FIELDS`. Add `_FLOAT_FIELDS = {"floor_ratio", "recency_floor"}` near `_INT_FIELDS` and coerce in `set_config_value` (`514-524`):
```python
    if field_name in _FLOAT_FIELDS and isinstance(value, str):
        value = float(value)
```
`authority_weights` (a TOML float table) is edited via the config file directly — `memsearch config set` does not handle nested dict values; add a one-line code comment saying so. TOML int weights (`= 2`) load fine (arithmetic is unaffected).

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(config): AuthorityRerankConfig + float coercion (MON-XXX)"`

### Task 8: Wire authority/recency rerank into `search()` (rerank on candidates, before slice)

**Files:** Modify `src/memsearch/core.py` (`search()`); `tests/test_core_provenance.py`.

- [ ] **Step 1: Write the failing tests**
  - two stored chunks, equal embedding score, different filename dates, `authority_enabled=True` → recent one is `res[0]`.
  - an exact-identifier query (e.g. a 40-char hash) with a stale-dated exact match present → the exact match is NOT demoted by recency (current behaviour preserved; authority rerank skipped on the exact path).
  - **compose test:** `reranker_model` set to a sentinel + `monkeypatch` `memsearch.reranker.rerank` to a stub that returns its input re-sorted; `authority_enabled=True` → assert both ran (cross-encoder stub called, final order reflects recency). Proves decision #3.

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — final block of `search()` becomes (order matters):
```python
        # 1. optional cross-encoder (existing, unchanged, lines 243-246)
        # 2. branch:
        if exact_identifier:
            results = _prioritize_exact_identifier_matches(query, results)
        elif self._authority_rerank.enabled:
            from .provenance import rerank_by_authority_recency
            ar = self._authority_rerank
            results = rerank_by_authority_recency(
                results, weights=ar.authority_weights, half_life_days=ar.half_life_days,
                recency_floor=ar.recency_floor, floor_ratio=ar.floor_ratio, today=today)
        # 3. slice THEN enrich (enrich only touches <= top_k rows)
        results = results[:top_k]
        return enrich(results, author=self._author, scope=self._citation_scope,
                      today=today, stale_after_days=self._stale_after_days)
```
Update the `search()` docstring: authority/recency floor-gating may return **fewer than `top_k`** results (low-relevance noise is dropped).
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(core): default authority/recency rerank on recall (MON-XXX)"`

---

## Phase 3 — Coverage / gap probe (honest partial/absent) — *reviewer flagged as cuttable; Dom to confirm*

*Lets an "absent" answer say "I checked logs back to <date>, nothing on this" with real evidence — Simon's `memory-meta.sh` equivalent.*

### Task 9: `coverage` CLI command

**Files:** Modify `src/memsearch/cli.py` (new `@cli.command("coverage")`); test `tests/test_cli_coverage.py`.

- [ ] **Step 1: Failing test** — `CliRunner`, monkeypatch `MilvusStore.indexed_sources()` (exists, `store.py:241`) to return dated + undated paths; assert `--json-output` has `earliest`, `latest`, `dated_source_count`, `undated_source_count`, `gaps` (list of `[start, end, days]` where consecutive dated days are >`gap_days` apart).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — `coverage` reads `mem.store.indexed_sources()`, runs `extract_file_date` over them, computes min/max, sorts unique dates, finds gaps > `--gap-days` (default 2), counts undated. `--json-output` emits the structure; human mode prints "Indexed memory spans 2026-04-02 → 2026-06-19 (N days); M undated sources; gaps: …".
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate.**
- [ ] **Step 6: Commit** — `git commit -m "feat(cli): coverage command for honest gap reporting (MON-XXX)"`

---

## Phase 4 — Recall skill citation contract

*Make the agent cite author + date + age + stale, and use `coverage` for partial/absent. Reconcile the bare repo copy with the deployed contract.*

### Task 10: Update the deployed recall skill (machine config — NOT a repo commit)

**Files:** Modify `~/.claude/skills/memory-recall/SKILL.md` (Answer contract `35-58`).

- [ ] **Step 1:** Update the `Evidence:` line to require `author · source:line · date (Nd ago)` and a `⚠ stale` note when `stale`. For `Status: absent`/`partial`, run `memsearch coverage --json-output` and cite the indexed date-range + gaps as evidence of what was searched.
- [ ] **Step 2:** Add a worked example: *"You set the third pricing tier at £37. Decided by Dominic Monkhouse · `.memsearch/memory/2026-06-10.md:5-7` · 9 days ago. No newer pricing memory found (checked logs to 2026-06-19)."*
- [ ] **Step 3: Verify** — re-read; confirm the contract references author + `coverage`.
- [ ] **Step 4:** Report the change in chat. This file is outside the repo (Dom's machine config) — do NOT commit it to memsearch, and do NOT push Dom-specific failure-mode notes into the repo copy.

### Task 11: Reconcile the repo plugin copy

**Files:** Modify `plugins/claude-code/skills/memory-recall/SKILL.md` (currently 50 lines, no contract).

- [ ] **Step 1:** Port the *generic* citation/honesty contract (Status found/partial/absent, cite author·source:line·date·age, admit gaps, use `coverage`) into the repo copy. Do NOT copy Dom-specific failure-mode notes from the deployed skill (machine-specific — keep them out of the shared repo).
- [ ] **Step 2: Verify** — `grep -c "Status: found" plugins/claude-code/skills/memory-recall/SKILL.md` ≥ 1.
- [ ] **Step 3: Commit** — `git commit -m "docs(recall): add citation/honesty contract to plugin skill (MON-XXX)"`

---

## Risks & open decisions

- **mtime is not used for dating** (matches Simon): undated files (`MEMORY.md`, linear cards, imported chats) get no date/age and are never flagged stale. Acceptable — staleness only applies to dated daily logs.
- **Future-dated files clamp to 0 days** (`days_since`) — a clock-skewed or deliberately future-dated note reads as "0 days, fresh" rather than negative. Documented; benign.
- **Floor-gating returns < `top_k`** when results are low-relevance (intended noise reduction). Consumers that count results (the recall skill, any downstream) may see fewer than requested. Documented in the `search()` docstring; the recall skill should not assume exactly `top_k` rows.
- **`today` is injectable into `search()`** for deterministic tests; prod passes `None` → `date.today()`. Any test asserting `stale`/`days_since` MUST pass an explicit `today`, or it becomes a time-bomb as wall-clock advances past `stale_after_days`.
- **Performance:** rerank runs on the candidate set (`fetch_k` ≈ `top_k*3` ≈ 30 dicts for normal queries); enrich runs only on `top_k` rows (after slice) — so the widened exact-identifier `fetch_k` (up to `count()`) is NOT enriched per-row. Pure-Python, no DB round-trip, no model. Negligible (<1ms). Not a query-plan change → no `EXPLAIN` needed.
- **Authority weights are corpus-specific heuristics** — defaults target MemSearch's layout; tune via `[authority_rerank]` after eyeballing real recall.
- **Team transition cost (deferred):** stored `author`/`scope` field (schema + one reindex), scope filter in `MilvusStore.search()`, and `resolve_attribution()` reads stored metadata. Seam built so nothing else changes.

---

## Review status

- **Plan-document-reviewer (Claude): ✅ findings incorporated** — C1 (CLI wiring via `_cfg_to_memsearch_kwargs`), C2 (required `_FLOAT_FIELDS` coercion), E1 (enrich-after-slice ordering + `today` param), T1/T2 (real fake-store helper + real-`__init__` test), T3/T5 (top-survives + compose tests). Recommendations surfaced to Dom: (a) **cut Phase 3 to a follow-up** — kept pending Dom's call; (b) Task 10 reframed as machine-config (not a repo commit).
- **Cross-model adversarial review (Codex via /ap-check): _pending — run next, sequentially_**

---

## Codex / ap-check review fixes

_(to be appended after the adversarial review)_
