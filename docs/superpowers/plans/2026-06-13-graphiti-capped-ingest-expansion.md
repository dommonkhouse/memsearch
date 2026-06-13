# Graphiti Capped Ingest Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Graphiti relationship recall from the current 3-episode curated seed to reviewed capped batches, proving each batch improves search quality without full-memory ingestion.

**Architecture:** Keep Markdown and vector search as the source of truth and primary recall path. Treat Graphiti as a derived sidecar in group `ms_memsearch_active_curated_v1`, fed only from reviewed curated source files or explicit seed files, with dry-run, cap, manifest checkpoint, evaluation, and rollback at every batch.

**Tech Stack:** Python 3.10+, MemSearch CLI, Graphiti MCP, FalkorDB, `.memsearch/graphiti-curated-manifest.json`, `uv run memsearch graph-index-curated`, `uv run memsearch graph-eval`, pytest.

---

## Evidence Checked

- Current production Graphiti group is `ms_memsearch_active_curated_v1`.
- Current manifest is `.memsearch/graphiti-curated-manifest.json`.
- Current manifest has 3 episodes from only:
  - `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md`
  - `docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md`
- `uv run memsearch graph-eval --json-output` passed 7 of 7 after PR #2 was merged.
- `uv run memsearch graph-status` reports Graphiti MCP running and connected to FalkorDB.
- `src/memsearch/graphiti/curated.py` already excludes raw chat/session/code dump folders and only selects durable curated Markdown sources.
- `uv run memsearch graph-index-curated --help` confirms the required safety controls exist: `--dry-run`, `--limit`, `--group-id`, `--manifest-path`, `--force`, endpoint, host header, and timeout flags.
- Graphiti MCP official README, checked on 2026-06-13, documents episode management, `group_id` filtering, fact/node search, graph clearing, and FalkorDB as a supported/default backend: https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- FalkorDB Graphiti MCP docs, checked on 2026-06-13, document episode management, group management, fact/node search, and graph maintenance: https://docs.falkordb.com/agentic-memory/graphiti-mcp-server.html

## Current State

- PR #2 is merged into `dommonkhouse/memsearch:main` at merge commit `99961250ce2b2538e69d933597517e8c449bc464`.
- The current graph has not had a full `.memsearch/memory` ingest.
- The last attempted broader source rebuild showed why blind ingestion is risky: Graphiti lifted historical NordVPN/Tailscale troubleshooting symptoms as current facts.
- The corrected production graph is intentionally seed-led and scoped.

## Non-Negotiable Rules

- Do not ingest the full `.memsearch/memory` folder.
- Keep Graphiti group `ms_memsearch_active_curated_v1`.
- Keep manifest `.memsearch/graphiti-curated-manifest.json`.
- Keep default vector search as primary.
- Preserve exact vector lookup quality for `MON-316`, `MON-259`, paths, SHAs, and branch names.
- Graphiti failure must fall back cleanly to vector search.
- No full-memory ingestion without dry-run, cap, review, and explicit approval.
- No direct ingestion of broad historical troubleshooting notes unless their current-state risk has been reviewed.
- Do not clear the production curated group unless a rollback or rebuild step explicitly requires it.

## Files and Responsibilities

- Modify: `src/memsearch/graphiti/evaluation.py`
  - Add relationship cases and negative controls before any new batch is ingested.
- Modify: `tests/test_graphiti_cli.py` or related graph tests
  - Cover any new evaluation, scoring, filtering, or fallback behaviour if code changes are required.
- Create: `docs/graphiti-curated-seeds/2026-06-13-capped-batch-001.md`
  - Hand-curated relationship facts for the first expansion batch.
- Optional create: `docs/graphiti-curated-seeds/2026-06-13-capped-batch-001-sources.md`
  - Review notes mapping each seed statement back to the source file and line or Linear evidence.
- Optional modify: `docs/cli.md`
  - Document the capped curated ingestion workflow if the commands or guardrails need to be made operator-visible.
- Do not track `.memsearch/graphiti-curated-manifest.json`; it remains runtime state.

## Not Included In This Version

- **Full `.memsearch/memory` ingestion:** not included because it previously created stale current-state recall. Reconsider only after at least two capped batches improve recall without regressions.
- **Automatic prompt injection changes:** not included. Graph recall quality must be proven independently first.
- **Replacing vector search:** not included. Vector search remains the primary recall path.
- **Bulk direct ingestion of every `claude-config/memory` file:** not included. Use explicit file lists or seed distillation.
- **Graphiti schema customisation:** not included unless evaluation shows extraction quality cannot improve with seed wording and source selection.

## Acceptance Criteria

- Baseline graph evaluation passes before any ingest.
- A manifest checkpoint is created before each batch.
- Batch 001 dry-run shows the exact selected file count, excluded file count, episode count, and pending episode count.
- Batch 001 is capped at no more than 10 new episodes.
- After ingestion and async extraction, `uv run memsearch graph-eval --json-output` passes 100 percent.
- Practical relationship queries show new useful graph facts and no stale NordVPN/Meshnet current-state facts.
- Exact vector controls remain unchanged for `MON-316`, `MON-259`, the branch name, and at least one commit SHA.
- Linear MON-316 is updated with the batch size, sources, manifest count, evaluation result, and keep/remove decision.
- Rollback is immediately executable from the saved checkpoint and the two known-good seed files.

## Rollback Plan

If any batch causes stale facts, negative-control failures, or vector recall regression:

1. Save the failing graph-search output and manifest for evidence.
2. Clear only group `ms_memsearch_active_curated_v1`.
3. Restore `.memsearch/graphiti-curated-manifest.json` from the pre-batch checkpoint or reset episodes to `{}`.
4. Rebuild from the two known-good seed files only:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md \
  docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md \
  --limit 3
```

5. Poll `uv run memsearch graph-eval --json-output` until it returns `7 passed, 0 failed`.
6. Record the rejected batch and the reason in MON-316.

## Task 1: Baseline And Candidate Review

**Files:**
- No source edits unless evaluation cases are missing.

- [ ] **Step 1: Verify current runtime state**

Run:

```bash
uv run memsearch graph-status
uv run memsearch graph-eval --json-output
uv run python - <<'PY'
import json
from pathlib import Path
p = Path(".memsearch/graphiti-curated-manifest.json")
data = json.loads(p.read_text())
print(json.dumps({
    "group_id": data.get("group_id"),
    "episode_count": len(data.get("episodes", {})),
    "sources": sorted({v.get("source") for v in data.get("episodes", {}).values()}),
}, indent=2))
PY
```

Expected: Graphiti connected to FalkorDB, evaluation 100 percent pass, manifest group `ms_memsearch_active_curated_v1`, and 3 current episodes.

- [ ] **Step 2: Create a manifest checkpoint**

Run:

```bash
mkdir -p .memsearch/manifest-checkpoints
cp .memsearch/graphiti-curated-manifest.json \
  .memsearch/manifest-checkpoints/graphiti-curated-manifest-before-batch-001-$(date +%Y%m%d-%H%M%S).json
```

Expected: checkpoint file exists and contains the same `group_id` and episode count as the live manifest.

- [ ] **Step 3: Review candidate sources before writing seeds**

Start with these source families only:

- `docs/graphiti-falkordb.md`
- `docs/graphiti-falkordb-pilot-results.md`
- existing `docs/graphiti-curated-seeds/*.md`
- selected `claude-config/memory/projects/*.md` files only when the current-state wording is safe
- selected `claude-config/memory/tools/*.md` or `feedback/*.md` files only when they contain durable relationship facts

Exclude:

- `.memsearch/memory`
- raw transcripts
- imported sessions
- broad historical troubleshooting sections with obsolete symptoms

Expected: a short source list for Batch 001 with the reason each source is safe.

## Task 2: Expand The Evaluation Harness First

**Files:**
- Modify: `src/memsearch/graphiti/evaluation.py`
- Modify: tests covering graph evaluation if needed.

- [ ] **Step 1: Add relationship queries for the intended batch**

Add controls before ingesting new data. Suggested cases:

- current routing: `Is NordVPN still used or is this Tailscale only?`
- Mac Mini route: `What host should I use for the Mac Mini now NordVPN Meshnet is retired?`
- Graph sidecar: `How does Graphiti reach FalkorDB on the Mac Mini?`
- branch linkage: `How is dom/mon-316-graphiti-falkordb connected to Graphiti and FalkorDB?`

Expected: the existing graph still passes, and new cases either pass from current graph facts or fail in a known way that Batch 001 is designed to improve.

- [ ] **Step 2: Add negative controls**

Add at least:

- `Should I restart NordVPN Meshnet to fix MemSearch?`
- `Should I use .nord hostnames for Open Brain now?`
- unrelated MON issue query, for example `MON-249 homepage performance recovery`

Expected: graph must not recommend NordVPN, Meshnet restart, `.nord`, or unrelated MON linkage.

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run pytest tests/test_graphiti_cli.py tests/test_graphiti_curated.py -q
uv run memsearch graph-eval --json-output
```

Expected: tests pass and baseline evaluation result is recorded before ingest.

## Task 3: Build Batch 001 As Explicit Seeds

**Files:**
- Create: `docs/graphiti-curated-seeds/2026-06-13-capped-batch-001.md`
- Optional create: `docs/graphiti-curated-seeds/2026-06-13-capped-batch-001-sources.md`

- [ ] **Step 1: Write only extraction-friendly relationship statements**

Use short factual sentences, one relationship per line. Prefer:

- `X replaced Y for Z.`
- `X runs on Y.`
- `X connects to Y.`
- `X uses hostname Y.`
- `X is not part of current routing.`

Avoid:

- historical symptom lists
- ambiguous tense
- multi-paragraph troubleshooting prose
- stale hostnames unless they are explicitly labelled stale

Expected: the seed is reviewable and materially safer than direct ingestion of historical notes.

- [ ] **Step 2: Link every seed statement to evidence**

In the optional sources file, list each statement and the source file or Linear comment that proves it.

Expected: no invented facts and no uncited operational claims.

## Task 4: Dry-Run, Cap, And Ingest Batch 001

**Files:**
- Runtime only: `.memsearch/graphiti-curated-manifest.json`

- [ ] **Step 1: Dry-run exactly the intended batch**

Run:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/2026-06-13-capped-batch-001.md \
  --dry-run
```

Expected: selected count is 1, excluded count is 0, pending episode count is known before ingest.

- [ ] **Step 2: Apply a hard cap**

If pending episodes are more than 10, split the seed file before ingest. Otherwise run:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/2026-06-13-capped-batch-001.md \
  --limit 10
```

Expected: no more than 10 new episodes are queued.

- [ ] **Step 3: Wait for async extraction**

Poll:

```bash
uv run memsearch graph-eval --json-output
```

Expected: evaluation eventually reaches 100 percent pass. If it does not, stop and use the rollback plan.

## Task 5: Evidence Gate And Keep/Remove Decision

**Files:**
- No source edits unless a failing seed needs correction.

- [ ] **Step 1: Run practical relationship searches**

Run:

```bash
uv run memsearch search "Is NordVPN still used or is this Tailscale only?" --include-graph --top-k 5 --json-output
uv run memsearch search "What host should I use for the Mac Mini now NordVPN Meshnet is retired?" --include-graph --top-k 5 --json-output
uv run memsearch search "How does Graphiti relate to FalkorDB and Tailscale Serve in MON-316?" --include-graph --top-k 5 --json-output
```

Expected: graph facts improve the answer without displacing vector results or adding stale recommendations.

- [ ] **Step 2: Run exact vector controls**

Compare vector result hashes with and without graph for:

- `MON-316`
- `MON-259`
- `dom/mon-316-graphiti-falkordb`
- `8617ba4`
- `99961250ce2b2538e69d933597517e8c449bc464`

Expected: vector result ordering and chunk hashes are unchanged.

- [ ] **Step 3: Decide keep or remove**

Keep Batch 001 only if:

- evaluation passes
- practical graph facts are useful
- negative controls stay clean
- exact vector controls stay unchanged

Remove Batch 001 if any of those fail.

## Task 6: Commit, Push, And Track Evidence

**Files:**
- Commit only source files, tests, and docs.
- Do not commit `.memsearch/graphiti-curated-manifest.json`.

- [ ] **Step 1: Commit source changes**

Run the commit protocol, then commit the plan, tests, and seed files.

Expected: commit references MON-316 and includes no runtime manifest state.

- [ ] **Step 2: Push and open or update PR**

Expected: branch is pushed, PR includes the evaluation result, batch cap, and rollback status.

- [ ] **Step 3: Update Linear MON-316**

Record:

- batch source files
- dry-run counts
- cap used
- final manifest episode count
- graph evaluation result
- practical query evidence
- keep/remove decision

Expected: MON-316 remains the single tracking surface for Graphiti ingest expansion.
