# Codex Session Reingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover missing Codex session memory from MCB16 and the MacBook 14 backup without changing the Stop-hook default behaviour or indexing unreviewed raw transcripts.

**Architecture:** Extend the existing MON-321 chat-backfill lane with a focused Codex source slice: inventory live and backup rollout JSONL files, parse full rollouts only in explicit backfill mode, stage redacted review output, probe known missing memories, then promote the reviewed artefacts into the canonical MemSearch memory/index path. The live Stop hook remains final-turn only; reingest uses full-rollout parsing.

**Tech Stack:** Bash parser for Codex rollout formatting, Python backfill inventory/parser modules, pytest, existing `uv run python -m pytest` test gate, existing MemSearch index/search commands, Linear `MON` tracking.

**Parent Tracking:** Existing broad backfill lane: `MON-321` and `docs/superpowers/plans/2026-06-01-memsearch-chat-backfill.md`.

---

## Current State

- The Webwright install/session evidence exists in a Codex archived rollout, but it was not recoverable from normal MemSearch recall.
- Root cause is a Codex source-ingestion gap, not a Webwright-specific memory rule.
- `plugins/codex/scripts/parse-rollout.sh` is used by the live Stop hook and must continue to default to final-turn parsing.
- Backfill and investigation need an explicit full-rollout mode so earlier turns inside a multi-turn rollout are not lost.
- MCB16 structured inventory currently finds 2,593 Codex session/archive JSONL files.
- MacBook 14 is offline/missing, but the backup at `/Users/dominicmonkhouse/Backups/mac14-history-2026-06-25` contains 2,024 Codex session/archive JSONL files under `codex/sessions` and `codex/archived_sessions`.
- A broad filesystem search shows 2,036 Codex-looking JSONL paths in that backup, but 12 are not session/archive files: index/work files, a `codex/history.jsonl` file, and Claude project transcripts whose folder name contains `codex`.

## Files And Responsibilities

- Modify: `plugins/codex/scripts/parse-rollout.sh`
  - Preserve default final-turn output for the Stop hook.
  - Add explicit `--all` mode for full-rollout backfill and investigation.
- Modify: `src/memsearch/backfill/inventory.py`
  - Include live Codex archives under `.codex/archived_sessions`.
  - Include MacBook 14 backup layout under `codex/sessions` and `codex/archived_sessions`.
- Modify: `tests/test_codex_parse_rollout.py`
  - Prove default parsing returns only the final turn in a multi-turn rollout.
  - Prove `--all` includes earlier and later turns from the same rollout.
- Modify: `tests/backfill_chats/test_inventory.py`
  - Prove inventory includes live archives and backup-layout Codex sessions.
- Create or update: focused staging manifest under `.local/` or `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/`
  - Record source path, machine, file hash, parser mode, redaction status, and promotion status.
- Create or update: reviewed Codex reingest output under `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/`
  - Store redacted, reviewed, canonical markdown or card output only. Do not index raw JSONL.

## Not Included In This Version

- No deletion, archive, or cleanup of source sessions.
- No `memsearch reset`, destructive Milvus operation, or raw transcript indexing.
- No change to the live Codex Stop hook default. Full-rollout parsing is opt-in through `--all`.
- No Webwright-specific parser branch. Webwright is only a regression probe for one previously missing memory.
- No attempt to reconstruct missing MacBook 14 live state beyond the dated backup.
- No broad Claude, ChatGPT, Manus, or Antigravity reingest in this slice; those stay in the wider MON-321/source-sync lanes.

## Safety Gates

- Source files are read-only.
- Raw JSONL is never indexed directly.
- Staged output must pass secret scanning before review.
- Promoted output must pass secret scanning again before indexing.
- Indexing is explicit and separate from conversion.
- Verification must include both parser-level tests and recall probes against known missing Codex memories.

## Task 1: Parser Mode Split

**Files:**
- Modify: `plugins/codex/scripts/parse-rollout.sh`
- Test: `tests/test_codex_parse_rollout.py`

- [ ] **Step 1: Write generic multi-turn parser tests**

Add one fixture with two turns in a single rollout. Assert that default parsing excludes the earlier turn and includes only the final turn.

- [ ] **Step 2: Write explicit full-rollout parser test**

Use the same kind of fixture and assert that `--all` includes both earlier and later turns. Keep the fixture generic; do not encode a product/tool example as the requirement.

- [ ] **Step 3: Implement parser argument handling**

Add `--all`, `--last`, and help handling. Default to `last`.

- [ ] **Step 4: Verify targeted tests**

Run:

```bash
uv run python -m pytest tests/test_codex_parse_rollout.py tests/backfill_chats/test_parse_codex.py -v
```

Expected: all tests pass.

## Task 2: Codex Source Inventory Coverage

**Files:**
- Modify: `src/memsearch/backfill/inventory.py`
- Test: `tests/backfill_chats/test_inventory.py`

- [ ] **Step 1: Add inventory coverage test**

Add live archive and backup-layout fixture paths:

```text
.codex/archived_sessions/*.jsonl
codex/sessions/**/*.jsonl
codex/archived_sessions/*.jsonl
```

- [ ] **Step 2: Implement the inventory rules**

Add only those Codex session/archive rules. Do not include broad `*codex*` path matching.

- [ ] **Step 3: Verify source counts**

Run inventory for:

```text
/Users/dominicmonkhouse
/Users/dominicmonkhouse/Backups/mac14-history-2026-06-25
```

Expected planning counts:

```text
MCB16 Codex session/archive files: 2,593
MacBook 14 backup Codex session/archive files: 2,024
```

If a broader filesystem search returns a larger number, classify the extras before changing the rules.

## Task 3: Staged Conversion

**Files:**
- Modify or extend: existing backfill parser/render/manifest modules from MON-321
- Create: temporary conversion manifest/output under ignored `.local/` or the established imported-chats staging path

- [ ] **Step 1: Convert MCB16 Codex sessions in dry-run mode**

Use full-rollout parsing for conversion. Write a manifest with counts, hashes, skipped files, and parser errors.

- [ ] **Step 2: Convert MacBook 14 backup Codex sessions in dry-run mode**

Use the backup root as the source home. Keep machine identity as `MacBook 14 backup`.

- [ ] **Step 3: Summarise conversion health**

Report total files, converted conversations, skipped empty/unparseable files, parser errors, and duplicate candidates.

## Task 4: Secret Scan And Review Output

**Files:**
- Modify or use: existing redaction/secret-scan tooling from the backfill lane
- Create: reviewed Codex output under imported-chats staging

- [ ] **Step 1: Scan raw staged output**

Block promotion if API keys, bearer tokens, cookies, app passwords, SSH keys, or `.env` values are present.

- [ ] **Step 2: Generate reviewed canonical output**

Write redacted markdown/cards with source anchors, machine, rollout path, timestamp range, and clean user/assistant turns.

- [ ] **Step 3: Scan promoted output**

Run the same secret scan against the promoted review output.

## Task 5: Recall Probes Before Index Promotion

**Files:**
- No source edits unless probes expose a parser/render bug.

- [ ] **Step 1: Probe the known missing memory before promotion**

Search for the previously missing Codex install/setup memory. It is a regression probe only.

- [ ] **Step 2: Probe generic earlier-turn recovery**

Search for earlier-turn phrases from at least three multi-turn Codex rollouts that are not final-turn-only content.

- [ ] **Step 3: Record probe results**

Store the query, expected source rollout, and observed result in the conversion manifest or review notes.

## Task 6: Explicit Index Promotion

**Files:**
- Modify only generated memory/index artefacts in the established MemSearch memory store.

- [ ] **Step 1: Promote reviewed Codex output**

Promote only after Tasks 3-5 pass. Keep raw JSONL out of the index.

- [ ] **Step 2: Rebuild or refresh the index using the existing MemSearch path**

Use the current documented MemSearch indexing command for this repo/machine. Do not reset destructive state unless separately approved.

- [ ] **Step 3: Verify recall**

Run the same probes from Task 5 against normal MemSearch recall. Expected: known missing memories and generic earlier-turn probes are found with source anchors.

## Task 7: Live Capture Guard

**Files:**
- Inspect: Codex hook/config files that call `parse-rollout.sh`
- Modify only if the live hook explicitly needs an argument update

- [ ] **Step 1: Verify Stop hook still uses default final-turn behaviour**

Run or inspect the active Codex hook route and confirm no `--all` is used in live Stop-hook summarisation.

- [ ] **Step 2: Capture a tiny fresh Codex test session**

Confirm current live capture still writes a final-turn memory and does not ingest raw tool output.

- [ ] **Step 3: Document the split**

Document that live capture is final-turn, while backfill/reingest is full-rollout.

## Acceptance Criteria

- Parser tests prove final-turn default and explicit full-rollout mode.
- Inventory tests prove live archives and MacBook 14 backup layout are covered.
- MCB16 inventory reports 2,593 Codex session/archive JSONL files.
- MacBook 14 backup inventory reports 2,024 Codex session/archive JSONL files.
- The 12 broad-search extras are classified and excluded from session inventory.
- Staged Codex conversion has a manifest and passes secret scanning.
- Reviewed output, not raw JSONL, is promoted.
- Known missing Codex memory and generic earlier-turn probes resolve through normal MemSearch recall after indexing.
- Linear tracking references this focused plan and the parent MON-321 lane.
