# Manus MemSearch Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productise the Manus API backfill so all 622 exported Manus tasks can be safely recalled from MemSearch, then close the branch with verified code, data, and cleanup state.

**Architecture:** Keep three separate lanes: raw Manus export as source-of-truth, sanitised full Markdown as evidence, and compact session cards as the practical MemSearch recall layer. Canonical MemSearch ingestion must use the compact card lane, not raw event logs, because local ONNX embedding is too slow for full transcripts and because the card lane still links back to the full cleaned transcript.

**Tech Stack:** Python 3.11, Click CLI, pytest, Ruff, Milvus/MemSearch, Manus API, OpenAI `text-embedding-3-small` for the validated review collection.

---

## Current State

- Raw export completed for run `20260605-092248`: 622 tasks, 74,556 message events, 2,862 attachments, 2,775 downloaded, 0 export errors.
- Sanitised full Markdown exists at `.local/manus-api-indexable/20260605-092248`.
- Review MemSearch collection exists: `ms_manus_review_20260605_092248_cards_openai`.
- Review collection verification passed: 906 chunks and all 622 unique Manus task IDs present in indexed content.
- Canonical/default MemSearch collection has not been touched.
- Branch has uncommitted code/docs/tests for the Manus API backfill.
- Linear handoff is `MON-282`: https://linear.app/monkhouseandcompany/issue/MON-282/manus-memsearch-closeout-implementation-plan

## Not Included In This Version

- Full raw event-log indexing into MemSearch. It was tested and rejected because the ONNX provider was too slow and raw tool payloads made low-value embeddings.
- Irreversible deletion of raw export evidence. Raw export stays until Dom explicitly approves a retention policy.
- Dropping temporary Milvus review collections without a checkpoint. Temporary collections can be dropped only after recording names, dimensions, row counts, and confirming the final OpenAI card collection remains queryable.
- Canonical ingestion without a final source-to-index coverage check. Counts alone are not enough.

## File Structure

- Modify `src/memsearch/backfill/manus_api.py`: add reusable session-card rendering and optional MemSearch lane generation.
- Modify `src/memsearch/backfill/cli.py`: add a CLI command for generating compact Manus MemSearch cards from a promoted run.
- Modify `src/memsearch/backfill/render.py` only if card generation needs shared rendering helpers.
- Modify `tests/backfill_chats/test_manus_api.py`: cover card generation, task ID coverage, secret cleanliness, and full transcript pointers.
- Modify `tests/backfill_chats/test_cli.py`: cover the new CLI command.
- Modify `docs/backfill-chat-sources.md`: document the three-lane Manus export model and canonical ingestion command.
- Add or update `.gitignore`: keep `.local/` ignored if not already covered.
- No code should write directly to canonical MemSearch during tests.

## Risks And Gates

- Secret safety: `scan-secrets` must pass on every generated indexable and card lane.
- Coverage: every task ID in the promoted manifest must appear in the card lane and final collection.
- Search provider mismatch: OpenAI embeddings create a 1536-dimension collection; ONNX creates 1024. Searches against the OpenAI collection must pass `-p openai -m text-embedding-3-small`.
- Cleanup safety: local folders may be moved to Trash only when they are agent-created residue and not source-of-truth; Milvus collection drops need a checkpoint first.

## Task 1: Productise The Session-Card Lane

**Files:**
- Modify: `src/memsearch/backfill/manus_api.py`
- Modify: `tests/backfill_chats/test_manus_api.py`

- [ ] **Step 1: Write failing tests for card generation**

Add tests that build a tiny exported Manus run, promote it, generate session cards, and assert:
- one card heading per task
- `Manus task ID` appears exactly once per task
- `Full cleaned transcript` points at the promoted full Markdown
- raw signed URLs and obvious secrets are absent
- user request and assistant outcome excerpts are retained

Run: `uv run pytest tests/backfill_chats/test_manus_api.py -q`
Expected: FAIL because card generation is not exposed as a reusable function.

- [ ] **Step 2: Implement minimal card generation**

Add a function such as:

```python
def generate_manus_memsearch_cards(promoted_dir: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    ...
```

The function should read promoted full Markdown, split only on `## Manus Api session`, summarise each session into a card, and return counts:
- `task_cards`
- `markdown_files`
- `unique_task_ids`
- `output_dir`

- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/backfill_chats/test_manus_api.py -q`
Expected: PASS.

## Task 2: Add CLI For Card Lane Generation

**Files:**
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `tests/backfill_chats/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a `CliRunner` test for:

```bash
uv run python -m memsearch.backfill.cli manus-cards --promoted <dir> --output <dir>
```

Expected JSON includes `task_cards`, `unique_task_ids`, and `output_dir`.

- [ ] **Step 2: Add CLI command**

Add `manus-cards` with:
- `--promoted`
- `--output`
- `--force`

It must refuse to overwrite existing output without `--force`.

- [ ] **Step 3: Run CLI tests**

Run: `uv run pytest tests/backfill_chats/test_cli.py -q`
Expected: PASS.

## Task 3: Canonical Ingestion Proof

**Files:**
- Modify: `docs/backfill-chat-sources.md`
- No production collection mutation without final confirmation in the executing session.

- [ ] **Step 1: Document the exact reviewed command**

Document the validated review command:

```bash
memsearch index .local/manus-api-memsearch-cards/20260605-092248/memory/manus_cloud/manus_api \
  -c ms_manus_review_20260605_092248_cards_openai \
  -p openai \
  -m text-embedding-3-small \
  --force \
  --max-chunk-size 3000
```

- [ ] **Step 2: Add canonical ingestion checklist**

Document that canonical ingestion requires:
- source manifest count
- generated card task ID count
- final collection row count
- unique task IDs in indexed content
- targeted recall searches

- [ ] **Step 3: Run documentation and targeted test gate**

Run:

```bash
uv run pytest tests/backfill_chats
uv run ruff check src/memsearch/backfill tests/backfill_chats docs/backfill-chat-sources.md
```

Expected: PASS.

## Task 4: Cleanup And Retention Checklist

**Files:**
- Modify: `docs/backfill-chat-sources.md`

- [ ] **Step 1: Record cleanup candidates**

Record temporary collections found during closeout:
- `ms_manus_review_20260605_092248`
- `ms_manus_review_20260605_092248_cards`
- `ms_manus_review_20260605_092248_chunk12000`
- `ms_manus_review_20260605_092248_compact_3000`
- `ms_manus_review_20260605_092248_memsearch`
- `ms_manus_review_20260605_092248_memsearch_1500`

Keep final review collection:
- `ms_manus_review_20260605_092248_cards_openai`

- [ ] **Step 2: Checkpoint before any destructive cleanup**

Before dropping any Milvus collection, write a local JSON report with name, row count, dimension, and sample query evidence.

- [ ] **Step 3: Reversible local cleanup only**

Move agent-created debug folders to Trash only after listing them:
- `.local/debug-export-one`
- `.local/debug-invalid-url`

Do not trash `.local/manus-api-export/20260605-092248` or `.local/manus-api-indexable/20260605-092248`.

## Task 5: Branch Closeout

**Files:**
- All modified source, test, docs, and plan files.

- [ ] **Step 1: Run final targeted verification**

Run:

```bash
uv run pytest tests/backfill_chats
uv run ruff check src/memsearch/backfill tests/backfill_chats docs/backfill-chat-sources.md
```

Expected: PASS.

- [ ] **Step 2: Record known repo-wide lint exception**

If repo-wide Ruff still fails only because of unrelated pre-existing files outside this work, record that in the closeout rather than fixing unrelated files.

- [ ] **Step 3: Commit**

Commit the branch with a message that references the Linear issue if one exists. If Linear is still unavailable, use:

```bash
git commit -m "feat: add Manus API backfill"
```

- [ ] **Step 4: Final report**

Report by lane:
- code
- review collection
- canonical ingestion status
- cleanup status
- Linear status
- remaining approval-only items

## Review Status

- Plan-document reviewer: skipped. This is a closeout plan for already implemented branch work, and Dom explicitly said “do it all”.
- Cross-model adversarial review: skipped for the same reason; execute with targeted verification instead.
- Linear handoff: MON-282 — https://linear.app/monkhouseandcompany/issue/MON-282/manus-memsearch-closeout-implementation-plan
