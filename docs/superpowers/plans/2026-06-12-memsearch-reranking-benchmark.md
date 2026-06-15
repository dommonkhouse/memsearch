# MemSearch Reranking Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark-first reranking rollout path for MemSearch so we can prove whether cross-encoder reranking improves memory recall before enabling it by default.

**Architecture:** MemSearch already has a cross-encoder reranker in `src/memsearch/reranker.py` and CLI/config wiring via `--reranker-model` / `reranker.model`. This plan does not rebuild reranking. It adds a reproducible evaluation harness, source-diversity/dedup tests, docs for safe rollout, and a guarded recommendation for enabling the existing reranker only if benchmark results improve.

**Tech Stack:** Python 3.10+, Click, pytest, MemSearch CLI, ONNX reranker model `Alibaba-NLP/gte-reranker-modernbert-base`, optional Cohere comparison outside the default implementation.

---

## Scope decision

This is a single-repo, reversible, benchmark-first change. It is not a production deploy and it should not flip Dom's global MemSearch config by default. Per the writing-plans scope check, the implementation can run inline or in one focused worktree once approved. Dom explicitly requested adversarial review after the first draft, so the AP check must pass before this plan is treated as ready to execute.

## Evidence checked

- Existing MemSearch source:
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/reranker.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/core.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/config.py`
- Existing tests:
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_core.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_config.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_cli_help.py`
- Live smoke test on Dom's collection `ms_memsearch_ae2d4f9b`:
  - Plain search and `--reranker-model Alibaba-NLP/gte-reranker-modernbert-base` returned different ordering.
  - Reranked output exposed a risk: duplicate Linear-import chunks can dominate the top results.
- Upstream/community evidence:
  - MemSearch docs/repo describe persistent Markdown + Milvus memory and optional cross-encoder reranking.
  - BGE docs define rerankers/cross-encoders as query-document pair scorers for refining candidate order.
  - Cohere Rerank docs describe taking a query plus texts and returning relevance-scored ordering.
  - Alibaba `gte-reranker-modernbert-base` is a text ranking model suitable for rerank routes, not embedding routes.

## Files to create or modify

- Create: `/Users/dominicmonkhouse/Projects/memsearch/scripts/benchmark_reranking.py`
  - Runs a fixed query set against plain MemSearch and one or more reranker modes.
  - Writes JSON and Markdown summary output.
  - Scores expected source hits in top 1, top 3, and top 5.
  - Includes a fixture mode that replays saved JSON result snapshots through the scoring layer, so unit tests do not need Milvus, MemSearch data, Hugging Face downloads, or network access.
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_reranking_benchmark.py`
  - Unit tests for benchmark scoring, duplicate source grouping, and summary output.
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/core.py`
  - Add source-diversity/dedup support only if needed after benchmark harness tests prove duplicate dominance is a practical issue.
  - Keep default behaviour unchanged unless a config flag is added.
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/config.py`
  - Add a typed reranker setting only if source diversity needs config. The existing `reranker.model` already exists and should remain the main switch.
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
  - Add benchmark command only if the harness belongs in CLI. Otherwise keep it as a `scripts/` tool.
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/cli.md`
  - Document `--reranker-model`, `reranker.model`, safe benchmarking, and why recency is not the primary ranking signal.
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/home/configuration.md`
  - Add reranker configuration section.

## Not included in this version

- **Global config flip:** Do not set `reranker.model` globally until the benchmark passes.
- **PGLite/pgvector migration:** Not relevant to this work. This plan improves ranking on the existing MemSearch/Milvus path.
- **Recency-first reranking:** Recency may be reported or used as a tie-break later, but it must not overpower semantic relevance.
- **Cohere default dependency:** Cohere is useful as a comparison baseline because Open Brain uses it, but MemSearch's default pilot should stay local/ONNX first.
- **LLM answer synthesis:** This plan ranks chunks. It does not change answer-writing or memory citation policy.

## Acceptance criteria

- `scripts/benchmark_reranking.py` can run against saved JSON fixture snapshots without network access; this fixture mode verifies scoring/reporting only.
- Live benchmark mode can compare plain search vs ONNX reranker using a reviewed query manifest with expected source identifiers.
- The report includes hit@1, hit@3, hit@5, duplicate-source counts, median latency, and per-query diffs.
- Reranking is not recommended unless it improves expected-source hit rate without unacceptable duplicate-source collapse or latency.
- Documentation explains how to run the benchmark and how to enable reranking manually.
- Existing MemSearch defaults remain unchanged.

## Task 1: Benchmark manifest and scoring

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/scripts/benchmark_reranking.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_reranking_benchmark.py`

- [ ] **Step 1: Write tests for expected-source scoring**

Add tests that define a small in-memory result set and prove scoring works:

```python
def test_hit_scores_expected_source():
    results = [
        {"source": "/memory/old.md", "heading": "Wrong", "score": 0.9},
        {"source": "/memory/right.md", "heading": "Right", "score": 0.8},
    ]

    score = score_query_results(results, expected_sources=["/memory/right.md"])

    assert score.hit_at_1 is False
    assert score.hit_at_3 is True
    assert score.best_rank == 2
```

- [ ] **Step 2: Write tests for duplicate-source counting**

```python
def test_duplicate_source_counting():
    results = [
        {"source": "/linear/export-a.md", "heading": "MON-283"},
        {"source": "/linear/export-a.md", "heading": "MON-283"},
        {"source": "/memory/2026-06-06.md", "heading": "Session 11:07"},
    ]

    stats = source_diversity_stats(results)

    assert stats.unique_sources == 2
    assert stats.max_repeats_for_one_source == 2
```

- [ ] **Step 3: Implement pure scoring helpers**

Implement these pure functions first:

```python
def source_matches(actual: str, expected: str) -> bool:
    return expected in actual or actual.endswith(expected)

def score_query_results(results: list[dict], expected_sources: list[str]) -> QueryScore:
    ...

def source_diversity_stats(results: list[dict]) -> SourceDiversity:
    ...
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_reranking_benchmark.py -q
```

Expected: all new pure-function tests pass.

## Task 2: Benchmark runner

**Files:**
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/scripts/benchmark_reranking.py`
- Test: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_reranking_benchmark.py`

- [ ] **Step 1: Add CLI shape tests**

Test that the runner accepts:

```bash
python scripts/benchmark_reranking.py \
  --queries benchmark.json \
  --collection ms_memsearch_ae2d4f9b \
  --top-k 5 \
  --reranker-model Alibaba-NLP/gte-reranker-modernbert-base \
  --out outputs/reranking-benchmark.json
```

Do not add a `--candidate-k` flag in this version. Current MemSearch over-fetches reranker candidates internally as `top_k * 3` in `core.py`; tuning that ratio would require a separate API/CLI change and is outside this benchmark-first pass.

- [ ] **Step 2: Define query manifest format**

Use JSON so it is easy to generate and inspect:

```json
[
  {
    "id": "open-brain-sales-hiring",
    "query": "how do I hire good salespeople for my business",
    "expected_sources": ["open-brain-query-defaults.md", "How to hire the best salespeople"],
    "notes": "Known Open Brain recall example; use as a sanity check, not the only benchmark."
  }
]
```

The implementation must also include a small fixture manifest and saved result snapshots, for example under `tests/fixtures/reranking/`, so scoring/reporting tests can run without a live collection. Fixture mode replays saved result JSON; it does not prove live retrieval quality.

For the live benchmark, draft a 10-20 query manifest before running the final recommendation pass. The manifest needs Dom review because it defines what "better recall" means. Do not self-certify a global enablement recommendation from queries invented during the same run.

- [ ] **Step 3: Implement runner modes**

The runner should execute at least:

- `plain`: `memsearch search query --top-k N --json-output`
- `onnx-rerank`: same command with `--reranker-model Alibaba-NLP/gte-reranker-modernbert-base`
- `fixture`: load saved result snapshots and run the scoring/reporting code only

Do not implement Cohere inside the first version. Add a placeholder mode only if it is cleanly skipped when no API key exists.

- [ ] **Step 4: Capture latency**

Measure wall-clock time per query/mode with `time.perf_counter()`.

Warm the ONNX reranker before starting timed live measurements, either by a single throwaway reranked query or by loading the model cache explicitly. Record whether the model was already cached. First-run Hugging Face download time must not be mixed into steady-state latency.

Report:

- median latency
- p95 latency when enough queries exist
- per-query latency

- [ ] **Step 5: Write JSON and Markdown output**

Write:

- JSON for machine comparison
- Markdown summary for review

Expected Markdown headings:

- Overall scores
- Per-query winners
- Regressions
- Duplicate-source warnings
- Recommendation

## Task 3: Source diversity guard

**Files:**
- Modify only if benchmark proves duplicate dominance:
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/core.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/config.py`
- Test:
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_reranking_benchmark.py` or new focused test

- [ ] **Step 1: Decide whether code change is needed**

If at least 50% of live benchmark queries have three or more results from the same normalised source in the top 5, add a diversity guard. If duplicates are below that threshold, keep this out of code and leave it as a benchmark warning.

- [ ] **Step 2: Add a pure diversity helper if needed**

Preferred behaviour:

```python
def diversify_results(results: list[dict], max_per_source: int = 2) -> list[dict]:
    ...
```

Rules:

- Preserve score order.
- Keep at most `max_per_source` rows per normalised source key.
- Do not drop below requested `top_k` if replacement results exist.
- Normalise generated Linear/export paths where possible so regenerated timestamp folders do not appear as different sources.

- [ ] **Step 3: Wire only behind a config flag if needed**

Do not silently change default retrieval. If added, use a conservative config key such as:

```toml
[reranker]
model = ""
max_per_source = 0  # 0 means disabled
```

- [ ] **Step 4: Test no behaviour change by default**

Add a test proving existing search output remains unchanged when `max_per_source = 0`.

## Task 4: Documentation and rollout guide

**Files:**
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/cli.md`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/home/configuration.md`

- [ ] **Step 1: Document the existing reranker switch**

Add CLI examples:

```bash
memsearch search "query" --top-k 5 --reranker-model Alibaba-NLP/gte-reranker-modernbert-base
memsearch config set reranker.model Alibaba-NLP/gte-reranker-modernbert-base
memsearch config set reranker.model ""
```

- [ ] **Step 2: Document the benchmark gate**

State plainly:

- Run benchmark before enabling globally.
- Enable only if hit@3 improves and latency stays acceptable.
- Recency should be a tie-break or display field, not a primary ranking signal.

- [ ] **Step 3: Document rollback**

Rollback is:

```bash
memsearch config set reranker.model ""
```

If source diversity config is added:

```bash
memsearch config set reranker.max_per_source 0
```

## Task 5: Verification

**Files:**
- All modified files above.

- [ ] **Step 1: Run focused tests**

```bash
uv run pytest tests/test_reranking_benchmark.py tests/test_config.py tests/test_cli_help.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full test suite**

```bash
uv run pytest -q
```

Expected: all pass. If OpenAI-dependent tests are skipped because `OPENAI_API_KEY` is absent, record that as expected.

- [ ] **Step 3: Run formatter/linter**

```bash
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
```

Expected: zero findings.

- [ ] **Step 4: Run live benchmark on Dom's memory collection**

Use a reviewed query manifest with 10-20 known-answer cases. Include:

- recent known facts
- older known facts
- source-specific lookups
- queries where duplicate imported Linear cards previously dominate

Command:

```bash
python scripts/benchmark_reranking.py \
  --queries outputs/reranking-known-queries.json \
  --collection ms_memsearch_ae2d4f9b \
  --top-k 5 \
  --reranker-model Alibaba-NLP/gte-reranker-modernbert-base \
  --out outputs/reranking-benchmark.json
```

Expected: Markdown report says either "enable", "do not enable", or "needs source diversity first", with per-query evidence.

## Keep/remove threshold

Keep the reranker rollout path only if:

- hit@3 improves or stays equal while answer quality visibly improves
- no important known-answer query regresses from top 3 to absent
- median latency is acceptable for interactive recall
- duplicate-source dominance is controlled or explicitly flagged

Remove or defer global enablement if:

- quality is neutral or worse
- source duplicates dominate the top 5
- first-run model download or steady-state latency makes recall feel sluggish
- benchmark cannot explain its recommendation with source-level evidence

## Execution notes

- Do not run `memsearch config set reranker.model ...` globally during implementation unless Dom explicitly approves.
- Do not add recency weighting as the first shipped change.
- Commit in small steps:
  1. benchmark scoring helpers and tests
  2. runner implementation
  3. optional source diversity guard
  4. docs
- Commit messages should reference the owning Linear issue once created.

## Review status

- Plan-document-reviewer: skipped under writing-plans small-work rule; this is one repo, reversible, and benchmark-first.
- Cross-model adversarial review: CLEAN PASS on attempt 2 by Claude interactive after Dom explicitly invoked AP check.
- Linear handoff: MON-322 - https://linear.app/monkhouseandcompany/issue/MON-322/memsearch-reranking-benchmark-implementation-plan
