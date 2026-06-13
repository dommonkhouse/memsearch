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
- This plan filename is date-stamped as a plan snapshot. Batch seed filenames are date-free because they are execution artefacts that may be retried or delayed.

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
- Create: `docs/graphiti-curated-seeds/capped-batch-001.md`
  - Hand-curated relationship facts for the first expansion batch.
- Create: `docs/graphiti-curated-seeds/capped-batch-001-sources.md`
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
- Every new evaluation case has an explicit expected pre-batch result and post-batch result before ingestion starts.
- Batch 001 dry-run shows the exact selected file count, excluded file count, episode count, and pending episode count.
- Batch 001 is capped at no more than 10 new episodes.
- After ingestion and async extraction, `uv run memsearch graph-eval --json-output` passes every expected case within the bounded polling window.
- Practical relationship queries show new useful graph facts and no stale NordVPN/Meshnet current-state facts.
- Exact vector controls remain unchanged for `MON-316`, `MON-259`, the branch name, and at least one commit SHA.
- Linear MON-316 is updated with the batch size, sources, manifest count, evaluation result, and keep/remove decision.
- Rollback is immediately executable from the saved checkpoint and the two known-good seed files.

## Rollback Plan

If any batch causes stale facts, negative-control failures, or vector recall regression:

1. Save the failing graph-search output and manifest for evidence.
2. Clear only group `ms_memsearch_active_curated_v1`.
3. Restore `.memsearch/graphiti-curated-manifest.json` from the pre-batch checkpoint or reset episodes to `{}`.
4. Dry-run the two known-good seed files only and verify the pending count is exactly 3:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md \
  docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md \
  --dry-run
```

Expected: `2 scanned, 2 selected, 0 excluded, 3 episodes, 3 pending`. If the count differs, stop and inspect the seed files before rebuilding.

5. Rebuild from those same two known-good seed files only:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md \
  docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md \
  --limit 3
```

`--limit 3` caps queued episodes, not files. After the rebuild, read `.memsearch/graphiti-curated-manifest.json` and verify the manifest has exactly 3 episodes before polling evaluation.

6. Poll `uv run memsearch graph-eval --json-output` until it passes the recorded total case count with zero failures, with a maximum of 12 attempts at 10-second intervals.
7. Record the rejected batch and the reason in MON-316.

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
git check-ignore -v .memsearch/manifest-checkpoints/example.json
```

Expected: checkpoint file exists and contains the same `group_id` and episode count as the live manifest. `git check-ignore` confirms checkpoint files under `.memsearch/manifest-checkpoints/` are ignored.

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

Safety checklist for any direct source file:

- Reject direct ingestion if the file contains historical operational symptoms unless those symptoms are explicitly current.
- Reject direct ingestion if the file contains `NordVPN`, `Meshnet`, `.nord`, `100.87.225.99`, `troubleshooting`, `recovery`, or `migration` unless the source review explicitly labels each relevant statement as current, stale, or historical.
- Prefer seed distillation over direct ingestion when a file mixes current facts with historical failure modes.
- Require a negative control for every stale operational route mentioned in the reviewed source.

## Task 2: Expand The Evaluation Harness First

**Files:**
- Modify: `src/memsearch/graphiti/evaluation.py`
- Modify: tests covering graph evaluation if needed.

- [ ] **Step 1: Add relationship queries for the intended batch**

Add controls before ingesting new data. Suggested cases:

- current routing: `Is NordVPN still used or is this Tailscale only?` — expected pre-batch graph result: pass, with graph facts saying Tailscale replaced NordVPN/Meshnet and NordVPN/Meshnet are not current. This is a regression guard for the current-state correction.
- Mac Mini route: `What host should I use for the Mac Mini now NordVPN Meshnet is retired?` — expected pre-batch graph result: pass, with graph facts for `dom-kamet.tailf78a36.ts.net` and `100.72.169.59`. This is a regression guard for the route facts already in the 3-episode seed.
- Graph sidecar: `How does Graphiti reach FalkorDB on the Mac Mini?` — expected pre-batch graph result: pass, with Graphiti, FalkorDB, Mac Mini, and Tailscale Serve facts. This is a regression guard for MON-316 sidecar recall.
- branch linkage: `How is dom/mon-316-graphiti-falkordb connected to Graphiti and FalkorDB?` — expected pre-batch graph result: pass, with branch and Graphiti/FalkorDB facts. This is a regression guard for branch relationship recall.

For later batch-specific cases, state the expected pre-batch result and the expected post-batch result before ingesting. A case may be expected to fail pre-batch only if Batch 001 is explicitly designed to add that missing relationship.

- [ ] **Step 2: Add negative controls**

Add at least:

- `Should I restart NordVPN Meshnet to fix MemSearch?` — expected pre-batch and post-batch result: pass by not recommending NordVPN or Meshnet restart.
- `Should I use .nord hostnames for Open Brain now?` — expected pre-batch and post-batch result: pass by not recommending `.nord` hostnames.
- unrelated MON issue query, for example `MON-249 homepage performance recovery` — expected pre-batch and post-batch result: pass by not linking Graphiti/FalkorDB to the unrelated issue.

Expected: graph must not recommend NordVPN, Meshnet restart, `.nord`, or unrelated MON linkage.

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run pytest tests/test_graphiti_cli.py tests/test_graphiti_curated.py -q
uv run memsearch graph-eval --json-output
```

Expected: tests pass and baseline evaluation result is recorded before ingest, including total case count. Every new case must match its stated pre-batch result before proceeding to seed writing. The post-batch pass count must equal that recorded case count with zero failures.

## Task 3: Build Batch 001 As Explicit Seeds

**Files:**
- Create: `docs/graphiti-curated-seeds/capped-batch-001.md`
- Create: `docs/graphiti-curated-seeds/capped-batch-001-sources.md`

Use date-free batch filenames so retries or delayed execution do not create duplicate same-number batches with different dates. If a date is needed for evidence, put it inside the file body.

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

In `docs/graphiti-curated-seeds/capped-batch-001-sources.md`, list each statement and the source file, line range, PR, or Linear comment that proves it.

Example citation format:

```markdown
- Statement: Graphiti MCP connects to FalkorDB on the Mac Mini.
  Evidence: `docs/graphiti-falkordb.md:7-14`; MON-316 comment `2c6e07c4-e8d7-42e6-b959-31352f502314`.
```

Expected: no invented facts and no uncited operational claims.

## Task 4: Dry-Run, Cap, And Ingest Batch 001

**Files:**
- Runtime only: `.memsearch/graphiti-curated-manifest.json`

- [ ] **Step 1: Recheck Graphiti status before ingest**

Run:

```bash
uv run memsearch graph-status
```

Expected: Graphiti MCP is running and connected to FalkorDB immediately before the ingest dry-run.

- [ ] **Step 2: Dry-run exactly the intended batch**

Run:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/capped-batch-001.md \
  --dry-run
```

Expected: selected count is 1, excluded count is 0, pending episode count is known before ingest.

- [ ] **Step 3: Refresh the manifest checkpoint immediately before ingest**

Run:

```bash
cp .memsearch/graphiti-curated-manifest.json \
  .memsearch/manifest-checkpoints/graphiti-curated-manifest-before-batch-001-preingest-$(date +%Y%m%d-%H%M%S).json
uv run python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path(".memsearch/graphiti-curated-manifest.json").read_text())
print(len(data.get("episodes", {})))
PY
```

Expected: a fresh checkpoint exists after the final dry-run and before the live capped ingest. Record the printed episode count as `manifest_before_count`. Keep `PY` as a standalone heredoc delimiter line; do not append Python code to it.

- [ ] **Step 4: Apply a hard cap**

If pending episodes are more than 10, split the seed file before ingest. Otherwise run:

```bash
uv run memsearch graph-index-curated \
  docs/graphiti-curated-seeds/capped-batch-001.md \
  --limit 10
```

Expected: no more than 10 new episodes are queued.

- [ ] **Step 5: Wait for async extraction with a bounded poll**

After ingest, verify the manifest delta before polling:

```bash
export EXPECTED_DELTA=REPLACE_WITH_QUEUED_EPISODE_COUNT
export BEFORE_COUNT=REPLACE_WITH_MANIFEST_BEFORE_COUNT
uv run python - <<'PY'
import json
import os
from pathlib import Path

expected_delta = int(os.environ["EXPECTED_DELTA"])
before_count = int(os.environ["BEFORE_COUNT"])
data = json.loads(Path(".memsearch/graphiti-curated-manifest.json").read_text())
after_count = len(data.get("episodes", {}))
print({"before": before_count, "after": after_count, "delta": after_count - before_count})
raise SystemExit(0 if after_count - before_count == expected_delta else 1)
PY
```

Expected: manifest delta equals the queued episode count from the capped ingest output.

Poll using the recorded case count from Task 2:

```bash
export EXPECTED_CASES=REPLACE_WITH_RECORDED_TOTAL_CASE_COUNT
success=0
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  eval_json="$(mktemp /tmp/mon316-graph-eval-XXXXXX.json)"
  eval_err="$(mktemp /tmp/mon316-graph-eval-XXXXXX.err)"
  if uv run memsearch graph-eval --json-output >"$eval_json" 2>"$eval_err" \
    && uv run python - "$eval_json" <<'PY'; then
import json
import os
import sys

path = sys.argv[1]
expected = int(os.environ["EXPECTED_CASES"])
with open(path) as f:
    data = json.load(f)
raise SystemExit(0 if data["passed"] == expected and data["failed"] == 0 else 1)
PY
    success=1
    rm -f "$eval_json" "$eval_err"
    break
  fi
  cat "$eval_err" >&2
  rm -f "$eval_json" "$eval_err"
  sleep 10
done
test "$success" = 1
```

Expected: evaluation reaches the recorded total case count with zero failures within 12 attempts. If it does not, stop and use the rollback plan.

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

Minimum pass criteria:

- Tailscale-only query: graph facts must include a current Tailscale-only or Tailscale-replaced-NordVPN fact, and must not recommend restarting NordVPN or Meshnet.
- Mac Mini route query: graph facts or node summaries must include `dom-kamet.tailf78a36.ts.net` or `100.72.169.59`, and must not recommend `.nord` hostnames.
- Graphiti/FalkorDB/Tailscale Serve query: graph facts or nodes must include Graphiti, FalkorDB, and Tailscale Serve.
- Any graph result mentioning NordVPN, Meshnet, `.nord`, or `100.87.225.99` must label it as stale, historical, removed, or not current.

- [ ] **Step 2: Run exact vector controls**

Compare vector result hashes with graph on and graph off for:

- `MON-316`
- `MON-259`
- `dom/mon-316-graphiti-falkordb`
- `8617ba4`
- `99961250ce2b2538e69d933597517e8c449bc464`

Use the literal graph-off command:

```bash
for query in \
  "MON-316" \
  "MON-259" \
  "dom/mon-316-graphiti-falkordb" \
  "8617ba4" \
  "99961250ce2b2538e69d933597517e8c449bc464"
do
  uv run memsearch search "$query" --no-graph --top-k 5 --json-output
done
```

Use the literal graph-on command:

```bash
for query in \
  "MON-316" \
  "MON-259" \
  "dom/mon-316-graphiti-falkordb" \
  "8617ba4" \
  "99961250ce2b2538e69d933597517e8c449bc464"
do
  uv run memsearch search "$query" --include-graph --top-k 5 --json-output
done
```

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

Use an explicit add list. Start with the expected list below, then add any other actually modified source, test, or docs files from `git status --short`. Do not use `git add .` or `git add -u`.

```bash
git add \
  src/memsearch/graphiti/evaluation.py \
  tests/test_graphiti_cli.py \
  docs/graphiti-curated-seeds/capped-batch-001.md \
  docs/graphiti-curated-seeds/capped-batch-001-sources.md \
  docs/superpowers/plans/2026-06-13-graphiti-capped-ingest-expansion.md
git commit -m "MON-316 expand capped graphiti ingest"
```

If `docs/cli.md` or another graph test file was modified, add that exact path too. Expected: commit references MON-316 and includes no runtime manifest state.

- [ ] **Step 2: Push and open or update PR**

Create the evidence file before running any PR command. Fill in the Step 3 template with actual batch evidence, write it to `/tmp/mon316-batch-001-evidence.md`, then verify it exists:

```bash
test -s /tmp/mon316-batch-001-evidence.md
```

Verify the expected fork remote exists, then push and update or create the PR:

```bash
git remote get-url fork
git push fork HEAD
gh pr view 3 --repo dommonkhouse/memsearch >/dev/null 2>&1 \
  && gh pr comment 3 --repo dommonkhouse/memsearch --body-file /tmp/mon316-batch-001-evidence.md \
  || gh pr create --repo dommonkhouse/memsearch --base main --head "$(git branch --show-current)" --title "MON-316 capped Graphiti ingest batch 001" --body-file /tmp/mon316-batch-001-evidence.md
```

Expected: the fork remote is verified, the branch is pushed, `/tmp/mon316-batch-001-evidence.md` exists before `gh pr` runs, and the PR includes the evaluation result, batch cap, and rollback status.

- [ ] **Step 3: Update Linear MON-316**

Record:

- batch source files
- dry-run counts
- cap used
- final manifest episode count
- graph evaluation result
- practical query evidence
- keep/remove decision

Use this template:

```markdown
Batch 001 capped Graphiti ingest result

Sources:
- `docs/graphiti-curated-seeds/capped-batch-001.md`
- `docs/graphiti-curated-seeds/capped-batch-001-sources.md`

Dry-run:
- scanned:
- selected:
- excluded:
- episodes:
- pending:

Cap used:
- limit:
- queued:

Manifest:
- group:
- before count:
- after count:
- checkpoint:

Evaluation:
- pre-batch cases:
- post-batch passed:
- post-batch failed:

Practical searches:
- Tailscale-only:
- Mac Mini route:
- Graphiti/FalkorDB/Tailscale Serve:

Exact vector controls:
- MON-316:
- MON-259:
- branch:
- 8617ba4:
- merge SHA:

Decision:
- keep/remove:
- reason:
- rollback needed:
```

Expected: MON-316 remains the single tracking surface for Graphiti ingest expansion.
