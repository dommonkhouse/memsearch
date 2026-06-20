# Citation, Provenance & Attribution for MemSearch Recall — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every MemSearch recall result carry a trustworthy citation — source path + line range + date + age + "decided by" attribution + a staleness flag — and rank results so the freshest, most authoritative memory wins, porting Simon Scrapes' Agentic OS citation/reranking model into MemSearch's native Python pipeline.

**Architecture:** Add a query-time enrichment + ranking layer (no Milvus schema change, no reindex). A new `provenance` module derives `date`/`days_since` from the source filename, stamps `author`/`scope` via a single `resolve_attribution()` seam (today returns the configured constant — Dom sets `citation.author = "Dominic Monkhouse (dominicmonkhouse)"` in his config; in team mode this one function reads per-chunk metadata), applies Simon's authority×recency×floor reranking on the **widened candidate set**, then slices to `top_k` and enriches. The CLI surfaces these fields in JSON and human output; a new `coverage` command backs honest "partial/absent" answers; the recall skills cite them.

**Tech Stack:** Python 3.11+, dataclass config (`tomllib`/`tomli_w`), Milvus (via `MilvusStore`), Click CLI, pytest. Pure-Python ranking maths (no model, no DB round-trip).

---

## Execution preamble (read before Task 1)

- **Branch:** create `feat/citation-provenance` off current `main` before any change. All commits land on that branch. **No push / no PR without Dom's explicit approval** (per project rules). The per-task commit steps below are local-branch commits that form the TDD rhythm — they are authorised by Dom's `/executing-plans` invocation; pushing is not.
- **Dom's identity is config, not a library default.** The dataclass default for `author` stays `""` (this repo is a public fork of `zilliztech/memsearch` — hardcoding Dom's name into a library default is wrong). Dom's identity is set in his config and tested as flowing through. (See Task 4 setup step + the ledger note on the rejected "hardcode default" suggestion.)

---

## Why this shape (key decisions)

1. **No reindex now.** `author` is a constant today; `date` is derivable from the source path. Both computed at query time — read path only, no Milvus schema change. Reindex deferred to the team phase.
2. **Team-forward seam.** All attribution flows through `resolve_attribution(result, ...)`. Team upgrade changes only that function + adds a scope filter; output schema, citation format, CLI/JSON, recall skills are already team-shaped.
3. **Authority×recency complements the cross-encoder, not replaces it.** Cross-encoder (`reranker.py:236`, opt-in, default off) = relevance. New authority×recency×floor pass = freshness + source-authority + noise-gate. They compose; `reranker.py` is untouched.
4. **Candidate window (critical):** `core.py:238` currently widens `fetch_k = top_k*3` **only when `_reranker_model` is set**. Authority rerank must ALSO widen `fetch_k`, else the store returns only `top_k` and a fresher item ranked beyond `top_k` can never be promoted — the headline feature would silently no-op. Fix in Task 5.
5. **Ordering:** `store.search(fetch_k)` → optional cross-encoder (with `top_k=fetch_k` when authority rerank is on, so it doesn't pre-truncate) → **either** exact-identifier prioritise **or** authority/recency rerank (on the full candidate set) → **slice `[:top_k]`** → **`enrich`** (so per-row date/author stamping only touches ~`top_k` rows, never the widened exact-identifier set). `search()` gains an injectable `today` for deterministic tests.
6. **Exact-identifier queries skip authority/recency rerank** (`core.py:236-248` widens `fetch_k` to `count()` and prioritises exact matches — recency-weighting would bury the exact hit).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `src/memsearch/provenance.py` | date/age, attribution resolver, enrichment, authority×recency×floor rerank | **Create** |
| `src/memsearch/config.py` | `CitationConfig` + `AuthorityRerankConfig`; `_FLOAT_FIELDS` coercion | Modify (`29-37`, `76-79`, `178-204`, `514-524`) |
| `src/memsearch/core.py` | `__init__` params; `search()` candidate-window + ordering + `today` + enrich/rerank | Modify (`51-85`, `205-249`) |
| `src/memsearch/cli.py` | `_cfg_to_memsearch_kwargs` carries citation kwargs; `source:line` + citation in human output; `coverage` command | Modify (`90-104`, `404-420`) + add command |
| `tests/test_cli_config_helpers.py` | existing exact-dict assertion of `_cfg_to_memsearch_kwargs` — must be updated | Modify (`59-87`) |
| `~/.claude/skills/memory-recall/SKILL.md` **and** `~/.codex/skills/memory-recall/SKILL.md` | cite author/date/age/stale; use `coverage` + `--no-graph`; both are separate non-symlink deployed dirs — machine config, NOT repo commits | Modify (2 deployed) |
| `plugins/{claude-code,codex,opencode,openclaw}/skills/memory-recall/SKILL.md` | add citation/honesty contract + `--no-graph` recall | Modify (4 repo copies) |
| `tests/test_provenance.py` | unit tests for all provenance functions | **Create** |
| `tests/test_core_provenance.py` | integration via `make_fake_memsearch` (models `tests/test_core_exact_identifiers.py:40-78`, **respects `top_k`**) + a real-`__init__` monkeypatch test | **Create** |
| `tests/test_cli_coverage.py` | `coverage` command output | **Create** |

---

## Not included in this version (Deferred Decisions)

- **Team scoping / row-level access control** — the GBrain model Simon admits he hasn't shipped. Deferred per Dom (solo until we flip to team). Convergence: extend `resolve_attribution()` + a stored `author`/`scope` field (schema + one reindex) + a scope filter in `MilvusStore.search()`. Seam built so it's additive.
- **Storing `author`/`date` per chunk in Milvus** — deferred (reindex cost); only needed when author varies.
- **LLM synthesis layer** — neither system has one; agent writes the cited answer from ranked chunks. Not building it.
- **Cross-encoder on by default** — tracked under `docs/superpowers/plans/2026-06-12-memsearch-reranking-benchmark.md` (MON-322). Untouched here.
- **Phase 3 (`coverage`) — flagged cuttable.** Plan-document-reviewer recommended splitting it to a follow-up (second CLI surface). Kept because honest partial/absent is part of Simon's model and `store.indexed_sources()` already exists (`store.py:241`). **Dom's call** — see Review status.

---

## Phase 1 — Provenance enrichment (date + age + author + stale)

### Task 1: Date extraction and age helpers

**Files:** Create `src/memsearch/provenance.py`; Test `tests/test_provenance.py`.

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

- [ ] **Step 2: Run → FAIL** (`uv run pytest tests/test_provenance.py -v`).
- [ ] **Step 3: Implement** (port of `agentic-os/scripts/lib/reranker.py:82-93`, injectable `today`)

```python
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

import math
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
```

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full gate** — `uv run pytest && uv run ruff check src tests && uv run ruff format --check src tests`.
- [ ] **Step 6: Commit (feature branch)** — `git commit -m "feat(provenance): date extraction + age helpers (MON-XXX)"`

### Task 2: Attribution resolver (team seam) + enrichment

**Files:** Modify `src/memsearch/provenance.py`; Test `tests/test_provenance.py`.

- [ ] **Step 1: Failing test**

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
    assert r["scope"] == "private" and r["date"] == "2026-06-10"
    assert r["days_since"] == 9 and r["stale"] is False

def test_enrich_flags_stale_beyond_threshold():
    out = enrich([{"source": "/x/memory/2026-05-01.md", "content": "c", "score": 0.9}],
                 author="A", scope="private", today=date(2026, 6, 19), stale_after_days=14)
    assert out[0]["stale"] is True

def test_enrich_undated_source_is_not_stale_and_date_none():
    out = enrich([{"source": "/x/MEMORY.md", "content": "c", "score": 0.9}],
                 author="A", scope="private", today=date(2026, 6, 19), stale_after_days=14)
    assert out[0]["date"] is None and out[0]["days_since"] is None and out[0]["stale"] is False
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement**

```python
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
        enriched.append({**r, "author": a, "scope": s,
                         "date": d.isoformat() if d else None, "days_since": age,
                         "stale": (age is not None and age > stale_after_days)})
    return enriched
```

- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.** **Step 6: Commit** `"feat(provenance): attribution resolver seam + enrichment (MON-XXX)"`

### Task 3: Authority/recency/floor reranker (provenance)

**Files:** Modify `src/memsearch/provenance.py`; Test `tests/test_provenance.py`.

- [ ] **Step 1: Failing test**

```python
from memsearch.provenance import authority_multiplier, recency_factor, rerank_by_authority_recency
WEIGHTS = {".memsearch/memory/": 1.0, "MEMORY.md": 2.0, "imported-chats/": 0.8}

def test_authority_exact_file_beats_directory():
    assert authority_multiplier("/x/bootstrap/MEMORY.md", WEIGHTS) == 2.0
def test_authority_defaults_to_one():
    assert authority_multiplier("/x/random/file.md", WEIGHTS) == 1.0
def test_recency_factor_halves_at_half_life():
    assert abs(recency_factor("/x/2026-06-05.md", half_life=14, today=date(2026,6,19)) - math.exp(-1)) < 1e-9
def test_recency_factor_one_for_undated():
    assert recency_factor("/x/MEMORY.md", half_life=14, today=date(2026,6,19)) == 1.0
def test_rerank_prefers_recent_at_equal_score():
    out = rerank_by_authority_recency(
        [{"source": "/x/memory/2026-04-01.md", "score": 0.9, "content": "old"},
         {"source": "/x/memory/2026-06-18.md", "score": 0.9, "content": "new"}],
        weights={}, half_life_days=14, recency_floor=0.7, floor_ratio=0.3, today=date(2026,6,19))
    assert out[0]["content"] == "new"
def test_rerank_floor_gates_low_scores():
    out = rerank_by_authority_recency(
        [{"source": "/x/2026-06-18.md", "score": 1.0, "content": "keep"},
         {"source": "/x/2026-06-18.md", "score": 0.05, "content": "drop"}],
        weights={}, half_life_days=14, recency_floor=0.7, floor_ratio=0.3, today=date(2026,6,19))
    assert [r["content"] for r in out] == ["keep"]
def test_rerank_top_result_always_survives_even_if_alone():
    out = rerank_by_authority_recency(
        [{"source": "/x/2026-01-01.md", "score": 0.001, "content": "only"}],
        weights={}, half_life_days=14, recency_floor=0.7, floor_ratio=0.3, today=date(2026,6,19))
    assert [r["content"] for r in out] == ["only"]
def test_rerank_tolerates_missing_or_bad_score():
    out = rerank_by_authority_recency(
        [{"source": "/x/2026-06-18.md", "content": "no score"},
         {"source": "/x/2026-06-18.md", "score": "bad", "content": "bad score"}],
        weights={}, half_life_days=14, recency_floor=0.7, floor_ratio=0.3, today=date(2026,6,19))
    assert len(out) >= 1
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — faithful port of `agentic-os/scripts/lib/reranker.py:49-159`, `today` injected:

```python
def authority_multiplier(source, weights):
    if not source:
        return 1.0
    path = source.replace("\\", "/")
    best_weight, best_len = None, -1
    for key, weight in weights.items():            # exact-file wins, longest key
        nkey = key.replace("\\", "/")
        if not nkey.endswith("/") and path.endswith(nkey) and len(nkey) > best_len:
            best_len, best_weight = len(nkey), weight
    if best_weight is not None:
        return best_weight
    best_len = -1
    for key, weight in weights.items():            # directory/prefix, longest key
        nkey = key.replace("\\", "/")
        if nkey.endswith("/") and (("/" + nkey) in ("/" + path) or path.startswith(nkey)) and len(nkey) > best_len:
            best_len, best_weight = len(nkey), weight
    return best_weight if best_len >= 0 else 1.0


def recency_factor(source, *, half_life, today):
    d = extract_file_date(source)
    if d is None:
        return 1.0
    return math.exp(-max((today - d).days, 0) / half_life)


def rerank_by_authority_recency(results, *, weights, half_life_days, recency_floor, floor_ratio, today):
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
        s2 = s1 * (recency_floor + (1.0 - recency_floor) * recency_factor(src, half_life=half_life_days, today=today))
        scored.append({**item, "_s2": s2})
    threshold = max(x["_s2"] for x in scored) * floor_ratio
    final = [{**{k: v for k, v in it.items() if not k.startswith("_")},
              "final_score": round(it["_s2"], 6), "reranked": True}
             for it in scored if it["_s2"] >= threshold]
    final.sort(key=lambda x: x["final_score"], reverse=True)
    return final
```
(All-zero scores → `threshold=0`, `0>=0` keeps everything — no crash, no empty result.)

- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.** **Step 6: Commit** `"feat(provenance): authority/recency/floor reranker (MON-XXX)"`

### Task 4: Config — `CitationConfig` + `AuthorityRerankConfig` + float coercion

**Files:** Modify `src/memsearch/config.py` (`29-37`, `76-79`, `178-204`, `514-524`); Test `tests/test_config.py`.

**Verified plumbing:** a flat-field dataclass needs registering in `MemSearchConfig` (`178-190`) + `_SECTION_CLASSES` (`193-204`) only — `_dict_to_config`'s generic `cls(**filtered)` handles scalar and plain-`dict` fields (no `_dict_to_llm_config`-style special case). **`_FLOAT_FIELDS` does not exist and must be added** (`config.py` has only `_INT_FIELDS`/`_BOOL_FIELDS`); without it `memsearch config set authority_rerank.floor_ratio 0.4` stores `"0.4"` (str) → `top * floor_ratio` raises `TypeError`.

- [ ] **Step 1: Failing test** — `CitationConfig`/`AuthorityRerankConfig` defaults; TOML override of `stale_after_days`, `half_life_days`, `floor_ratio`; and `set_config_value("authority_rerank.floor_ratio", "0.4")` round-trips to `float` 0.4.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement**

```python
@dataclass
class CitationConfig:
    author: str = ""          # "" => CLI display falls back to a generic owner label; Dom sets his identity in config
    scope: str = "private"    # team seam: system/team/client/private
    stale_after_days: int = 14

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
Register both in `MemSearchConfig` (`citation`, `authority_rerank`) + `_SECTION_CLASSES`. Add `"stale_after_days"`, `"half_life_days"` to `_INT_FIELDS`; add `_FLOAT_FIELDS = {"floor_ratio", "recency_floor"}` near `_INT_FIELDS` and coerce in `set_config_value` (`514-524`): `if field_name in _FLOAT_FIELDS and isinstance(value, str): value = float(value)`. Comment that `authority_weights` (nested table) is edited via the config file directly, not `memsearch config set`.

- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.**
- [ ] **Step 6: Setup (Dom's identity, not a library default):** run `uv run memsearch config set citation.author "Dominic Monkhouse (dominicmonkhouse)"` (writes global `~/.memsearch/config.toml`). Verify with `uv run memsearch config get citation.author`. This is the one place Dom's identity lives.
- [ ] **Step 7: Commit** `"feat(config): CitationConfig + AuthorityRerankConfig + float coercion (MON-XXX)"`

### Task 5: Core — `__init__` params + `search()` rewire (candidate window, order, `today`, enrich)

**Files:** Modify `src/memsearch/core.py` (`51-85`, `205-249`); Create `tests/test_core_provenance.py`.

**Fixture note (verified):** no `fake_memsearch_factory` exists; `tests/test_core.py` uses a real `MemSearch` gated on `OPENAI_API_KEY`. Build `make_fake_memsearch(...)` modelled on `tests/test_core_exact_identifiers.py:40-78` (`MemSearch.__new__`). It MUST set `_embedder`, `_store`, `_reranker_model`, `_author`, `_citation_scope`, `_stale_after_days`, `_authority_rerank`. The fake store MUST **record and respect `top_k`** (slice its return) so the candidate-window test is meaningful.

**Existing-test regression (verified):** the fake in `tests/test_core_exact_identifiers.py:73-78` sets only `_embedder`/`_store`/`_reranker_model`. The new `search()` reads `_authority_rerank.enabled` and calls `enrich(... self._author, self._citation_scope, self._stale_after_days)`, so that test will `AttributeError` under the full gate. As part of this task, add `_author=""`, `_citation_scope="private"`, `_stale_after_days=14`, `_authority_rerank=AuthorityRerankConfig(enabled=False)` to that existing fake (disabling authority rerank keeps its exact-identifier assertions unchanged).

- [ ] **Step 1: Failing tests**
  - `test_search_results_carry_citation_fields` — single dated result; assert `author/date/days_since/stale` (pass explicit `today=date(2026,6,19)`).
  - `test_recent_result_promoted_from_beyond_top_k` — store holds 12 rows; the only fresh-dated row sits at raw index 11; call `search(top_k=5, today=...)` with `authority_enabled=True`; assert the fresh row is in the returned top-5. (Proves `fetch_k` widening + rerank — fails if `fetch_k` isn't widened for authority.)
  - `test_exact_identifier_not_demoted_by_recency` — a stale-dated exact hash match present; assert it stays first (authority rerank skipped on exact path).
  - `test_cross_encoder_composes_with_authority` — set `reranker_model="x"`, `monkeypatch` **`memsearch.reranker.rerank`** (NOT `memsearch.core.rerank` — `search()` uses a function-local `from .reranker import rerank`, so patch the source module) to a stub returning input unsliced; `authority_enabled=True`; assert stub ran AND final order reflects recency.
  - `test_init_sets_citation_defaults` — monkeypatch `memsearch.core.get_provider` and `memsearch.core.MilvusStore` to fakes, construct real `MemSearch(...)`, assert `_author == ""`, `_stale_after_days == 14`, `_authority_rerank.enabled is True`. (No `...` no-op.)
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — `__init__` adds `author=""`, `citation_scope="private"`, `stale_after_days=14`, `authority_rerank=None` (→ `AuthorityRerankConfig()`); `search()` gains `today=None`. Rewire:
```python
        # fetch_k: widen when EITHER reranker is active (was: only cross-encoder)
        widen = bool(self._reranker_model) or self._authority_rerank.enabled
        fetch_k = top_k * 3 if widen else top_k
        if exact_identifier:
            fetch_k = max(fetch_k, top_k * 5, 1500, int(self._store.count()))
        results = self._store.search(embeddings[0], query_text=query, top_k=fetch_k, filter_expr=filter_expr)
        if self._reranker_model and results:
            from .reranker import rerank
            # pass full candidate window through cross-encoder when authority rerank will run after it
            ce_top_k = fetch_k if (exact_identifier or self._authority_rerank.enabled) else top_k
            results = rerank(query, results, model_name=self._reranker_model, top_k=ce_top_k)
        from datetime import date as _date
        from .provenance import enrich, rerank_by_authority_recency
        today = today or _date.today()
        if exact_identifier:
            results = _prioritize_exact_identifier_matches(query, results)
        elif self._authority_rerank.enabled:
            ar = self._authority_rerank
            results = rerank_by_authority_recency(results, weights=ar.authority_weights,
                half_life_days=ar.half_life_days, recency_floor=ar.recency_floor,
                floor_ratio=ar.floor_ratio, today=today)
        results = results[:top_k]
        return enrich(results, author=self._author, scope=self._citation_scope,
                      today=today, stale_after_days=self._stale_after_days)
```
Update `search()` docstring: authority floor-gating may return **fewer than `top_k`**.

- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.** **Step 6: Commit** `"feat(core): citation enrichment + candidate-window authority rerank (MON-XXX)"`

### Task 6: CLI — carry citation kwargs, show `source:line` + citation, fix the regression test

**Files:** Modify `src/memsearch/cli.py` (`90-104`, `404-420`) and **`tests/test_cli_config_helpers.py` (`59-87`, regression)**; Create `tests/test_cli_search_citation.py`.

**Verified:** `_cfg_to_memsearch_kwargs` (`90-104`) is the only `MemSearch` constructor path (call sites `297/369/559/1160/1256`). `test_cli_config_helpers.py:59-87` asserts the EXACT returned dict — adding keys breaks it, so it MUST be updated in this task. JSON `--json-output` defaults to the **graph-wrapped** shape (`--include-graph/--no-graph` defaults `True`, `cli.py:320-322`; wrapper at `394-401`) — citation tests/skills must use `--no-graph` or read the `vector` key.

- [ ] **Step 1: Failing tests**
  - extend `test_cli_config_helpers.py` expected dict with `author`, `citation_scope`, `stale_after_days`, `authority_rerank` (and set those on the `cfg` fixture).
  - `tests/test_cli_search_citation.py`: monkeypatch `memsearch.core.get_provider` + `memsearch.core.MilvusStore` to fakes (NOT `memsearch.store.MilvusStore`); config `[citation] author="Dominic Monkhouse (dominicmonkhouse)"`; run `search "q" --no-graph`; assert human output contains `decided by Dominic Monkhouse`, `2026-...`, and `:5-7` (line range); `search "q" --no-graph --json-output` includes `"author"` and `"days_since"`.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — add to `_cfg_to_memsearch_kwargs`:
```python
        "author": cfg.citation.author,
        "citation_scope": cfg.citation.scope,
        "stale_after_days": cfg.citation.stale_after_days,
        "authority_rerank": cfg.authority_rerank,
```
In the human-output loop, change the `Source:` line to include the line range and add a citation line:
```python
            loc = f"{source}:{r['start_line']}-{r['end_line']}" if r.get("start_line") is not None else source
            click.echo(f"Source: {loc}")
            ...
            author_disp = r.get("author") or "the owner"
            cite = f"  decided by {author_disp}"
            if r.get("date"):
                cite += f" · {r['date']} ({r['days_since']}d ago)"
            if r.get("stale"):
                cite += "  ⚠ stale"
            click.echo(cite)
```
- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.** **Step 6: Commit** `"feat(cli): citation kwargs + source:line citation output; fix kwargs regression test (MON-XXX)"`

---

## Phase 3 — Coverage / gap probe *(reviewer flagged cuttable; Dom to confirm)*

### Task 7: `coverage` CLI command

**Files:** Modify `src/memsearch/cli.py` (new `@cli.command("coverage")`); Test `tests/test_cli_coverage.py`.

**Verified pattern:** do NOT instantiate `MemSearch` (that runs embedding-provider setup). Follow the `stats` command (`cli.py:1342-1358`): `MilvusStore(uri=..., token=..., collection=..., dimension=None)` then `store.indexed_sources()` (`store.py:241-248`).

- [ ] **Step 1: Failing test** — `CliRunner`, monkeypatch `memsearch.store.MilvusStore.indexed_sources` to return dated + undated paths; assert `--json-output` has `earliest`, `latest`, `dated_source_count`, `undated_source_count`, `gaps` (`[start, end, days]` where consecutive dated days are >`gap_days`).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — instantiate `MilvusStore(..., dimension=None)`, run `extract_file_date` over `indexed_sources()`, compute min/max, unique sorted dates, gaps > `--gap-days` (default 2), undated count. `--json-output` emits the structure; human mode prints the span + gaps line.
- [ ] **Step 4: Run → PASS.** **Step 5: Full gate.** **Step 6: Commit** `"feat(cli): coverage command (MON-XXX)"`

---

## Phase 4 — Recall skill citation contract (all copies)

### Task 8: Deployed recall skills — BOTH Claude and Codex (machine config — NOT repo commits)

**Files (verified, two separate non-symlink dirs):** `~/.claude/skills/memory-recall/SKILL.md` (`35-58`) AND `~/.codex/skills/memory-recall/SKILL.md` (still has the old search command without `--no-graph` at line `66` and the old evidence contract at `40-58`/`109-111`). Both are the *active* deployed skills the runtimes load; both must change.

- [ ] **Step 1:** In BOTH files, update the `Evidence:` line to require `author · source:line · date (Nd ago)` + `⚠ stale` when stale. For `absent`/`partial`, run `memsearch coverage --json-output` and cite the indexed date-range + gaps.
- [ ] **Step 2:** In BOTH files, change the `memsearch search ...` recall command(s) to pass `--no-graph` (or read the `vector` key) so JSON carries citation fields directly. Add the worked example: *"You set the third pricing tier at £37. Decided by Dominic Monkhouse · `.memsearch/memory/2026-06-10.md:5-7` · 9 days ago. No newer pricing memory found (checked logs to 2026-06-19)."*
- [ ] **Step 3: Verify** — for each deployed file run `grep -nE "decided by|--no-graph|coverage|source:line|Status: found" <file>` and confirm the markers are present in both `~/.claude/...` and `~/.codex/...`.
- [ ] **Step 4:** Report in chat. Outside the repo — do NOT commit; do NOT push Dom-specific notes into the repo copies.

### Task 9: Repo plugin recall skills (all four copies)

**Files:** Modify `plugins/claude-code/skills/memory-recall/SKILL.md` (bare, 50 lines), `plugins/codex/...`, `plugins/opencode/...`, `plugins/openclaw/...`.

**Verified:** four repo copies exist; Codex uses the `codex` path. Each must (a) carry the generic citation/honesty contract, (b) use `memsearch search ... --no-graph` (or read `vector`) so JSON carries citation fields. Do NOT copy Dom-specific failure-mode notes into the repo.

- [ ] **Step 1:** Add the generic contract (Status found/partial/absent; cite author·source:line·date·age; admit gaps; use `coverage`; `--no-graph`) to all four copies.
- [ ] **Step 2: Verify** — `for p in plugins/*/skills/memory-recall/SKILL.md; do grep -lq "Status: found" "$p" || echo "MISSING: $p"; done` prints nothing.
- [ ] **Step 3: Commit** `"docs(recall): citation/honesty contract + --no-graph in all plugin recall skills (MON-XXX)"`

---

## Risks & open decisions

- **mtime not used for dating** (matches Simon): undated files get no date/age, never flagged stale. Acceptable.
- **Future-dated files clamp to 0 days** — benign.
- **Floor-gating returns < `top_k`** (intended noise reduction). Recall skills must not assume exactly `top_k` rows; documented in `search()` docstring.
- **`today` injectable** — any test asserting `stale`/`days_since` MUST pass explicit `today` or it's a wall-clock time-bomb.
- **Candidate window cost:** `fetch_k = top_k*3` (~30 rows) now also applies when authority rerank is on (default). Rerank/enrich are pure-Python over ~30/≤`top_k` rows — negligible. The widened exact-identifier set is NOT enriched per-row (enrich runs after slice). No DB-plan change → no `EXPLAIN` needed.
- **JSON shape:** recall depends on `--no-graph`; if a skill omits it, citation fields are nested under the graph wrapper's `vector` key. Both paths documented.
- **Authority weights are heuristics** — tune via `[authority_rerank]` after eyeballing real recall.
- **Team transition (deferred):** stored `author`/`scope` field (schema + one reindex), scope filter in `MilvusStore.search()`, `resolve_attribution()` reads stored metadata.

---

## Review status / ledger

- **Plan-document-reviewer (Claude): ✅** — folded: CLI via `_cfg_to_memsearch_kwargs`, required `_FLOAT_FIELDS`, enrich-after-slice + `today`, real fake-store helper + real-`__init__` test, top-survives + compose tests.
- **ap-check attempt 1 (Codex): findings folded.** All accepted except one partial-rejection.
- **ap-check attempt 2 (Codex): confirmed attempt-1 items resolved; 3 new blockers folded (see fixes below).**
- **ap-check attempt 3 (Codex): _pending_.**

---

## Codex / ap-check review fixes

**Attempt 1 (Codex) — resolutions:**
1. **Task-order bug** (config referenced before created) — FIXED: config is now Task 4, before core (Task 5) / CLI (Task 6); reranker port is Task 3.
2. **Candidate window not widened for authority rerank** (would silently no-op the headline feature) — FIXED: Task 5 widens `fetch_k` when `_reranker_model OR authority_rerank.enabled`; added `test_recent_result_promoted_from_beyond_top_k`.
3. **Cross-encoder pre-truncates before authority** — FIXED: Task 5 passes `top_k=fetch_k` to the cross-encoder when authority rerank will run after it.
4. **Tests pass without proving behaviour** (fake ignored `top_k`; `...` no-op `__init__` test) — FIXED: fake store records+respects `top_k`; real-`__init__` test via monkeypatched `get_provider`+`MilvusStore`.
5. **CLI test patched wrong module** — FIXED: patch `memsearch.core.get_provider` + `memsearch.core.MilvusStore`.
6. **`_cfg_to_memsearch_kwargs` regression** — FIXED: Task 6 updates `tests/test_cli_config_helpers.py:59-87` expected dict.
7. **Human output lacked line range** — FIXED: Task 6 prints `source:start-end`.
8. **`coverage` instantiated `MemSearch`** — FIXED: Task 7 uses `MilvusStore(..., dimension=None)` per the `stats` pattern.
9. **Recall-skill scope + JSON shape** — FIXED: Task 9 updates all four repo copies and mandates `--no-graph` (or read `vector`).
10. **Commit steps vs "no commits unless asked"** — RESOLVED: execution preamble scopes commits to a local `feat/` branch (authorised by `/executing-plans`); push/PR still needs explicit approval.
- **PARTIAL-REJECT:** Codex wanted `author` to default to `"Dominic Monkhouse (dominicmonkhouse)"` in `CitationConfig`/`__init__`. Rejected the *hardcoded library default* (this repo is a public fork of `zilliztech/memsearch`; baking Dom's name into the dataclass is wrong) — but accepted the underlying requirement: Task 4 Step 6 sets `citation.author` in Dom's config and Task 6 tests that the configured author flows through; CLI keeps `"the owner"` only as a defensive display fallback.

**Attempt 2 (Codex) — confirmed attempt-1 items resolved; 3 new blockers, all FIXED:**
11. **Existing `test_core_exact_identifiers.py` fake breaks** (sets only `_embedder`/`_store`/`_reranker_model`; new `search()` reads `_authority_rerank` + `_author`/`_citation_scope`/`_stale_after_days` → `AttributeError` under full gate) — FIXED: Task 5 adds the 4 new attrs to that existing fake (`_authority_rerank=AuthorityRerankConfig(enabled=False)` so its exact-identifier assertions are unchanged).
12. **Compose-test patch target wrong** (`search()` uses function-local `from .reranker import rerank`, so `memsearch.core.rerank` doesn't exist to patch) — FIXED: Task 5 compose test patches `memsearch.reranker.rerank`.
13. **Deployed Codex skill missed** (`~/.codex/skills/memory-recall/SKILL.md` is a separate non-symlink dir still without `--no-graph`) — FIXED: Task 8 now updates BOTH deployed skills (`~/.claude/...` and `~/.codex/...`) and verifies the markers in each.
