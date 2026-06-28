# Chat backfill sources

## Official export blocker

Official ChatGPT and Claude Chat export samples are not present yet.

Expected local placement:

```text
/Users/dominicmonkhouse/Projects/memsearch/.local/chat-exports/
```

Required samples before implementing official export parsers:

- ChatGPT export zip or extracted folder containing `conversations.json` or `chat.html`.
- Claude export zip or extracted folder containing official conversation JSON or HTML.

The backfill pipeline must not guess these export shapes. Export parsers stay blocked until real samples exist in `.local/chat-exports/`.

## Git safety

`.local/` is listed in `.gitignore`, so downloaded export archives placed under `.local/chat-exports/` will stay out of git.

## Current supported local sources

- Claude Code JSONL under `~/.claude/projects/`.
- Codex rollout JSONL under `~/.codex/sessions/`.
- Proven Claude Desktop/Cowork local-agent JSONL under `~/Library/Application Support/Claude/local-agent-mode-sessions/**/.claude/projects/**/*.jsonl`.

Current skipped sources:

- Claude Desktop audit logs.
- Claude Desktop subagent transcripts by default.
- Claude Desktop `claude-code-sessions` metadata, treated as possible Claude Code duplicates.
- ChatGPT and Claude cache files until official exports are available.
- Manus local app and browser files are probe-only. Current local files are Chromium cache and IndexedDB/LevelDB artefacts, not a proven transcript format.

## Antigravity / Gemini route

Antigravity/Gemini sessions are captured from local Gemini chat files and live Antigravity CLI transcripts:

```text
~/.gemini/tmp/*/chats/*.json
~/.gemini/antigravity-cli/brain/*/.system_generated/logs/transcript.jsonl
```

`last_conversations.json` is treated as a cache/id map only. It is not the transcript source and must not be used as the source of record for backfill.

Sessions default to 30-day retention, so the freshness route runs daily. Raw Gemini and Antigravity CLI logs can include tool output and local app state, so they are not indexed directly. The supported MemSearch source is the compact card output generated from those raw logs.

Supported commands:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity --machine "$(scutil --get ComputerName)" --dry-run --max-sessions 5
uv run python -m memsearch.backfill.cli source-sync antigravity --machine "$(scutil --get ComputerName)" --max-sessions 5
uv run python -m memsearch.backfill.cli scan-secrets /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards
rg -n "backfill-agent:antigravity|source:(gemini_cli_chat|antigravity_cli_transcript)|User request|Assistant outcome" /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli
uv run memsearch index /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli -c ms_antigravity_review_<run_id>_cards_openai -p openai -m text-embedding-3-small
```

Safety gates:

- Dry-run previews changed sessions and does not write `.local/source-sync-state/antigravity.json`.
- Non-indexing sync writes cards and updates state, but indexing remains skipped unless `--index` is explicitly passed.
- Card scan must pass before review indexing.
- First indexing goes only into a temporary review collection such as `ms_antigravity_review_<run_id>_cards_openai`.
- Canonical indexing waits for manual review of the cards, temporary collection, and proof searches.
- OpenBrain/Graphiti consumes the same compact card Markdown after review. Use `graph-index-curated` on the generated card file path, not on raw `~/.gemini/tmp` JSON or `~/.gemini/antigravity-cli/brain` JSONL.

## Manus route

Manus has a public API for creating and managing agent tasks, including multi-turn task messages. The supported route for Manus backfill is now the read-only API path:

- `task.list` for paginated task metadata.
- `task.listMessages` for paginated task event history.
- Attachment URLs from message payloads, downloaded immediately into the staged task folder.

Local Manus app/browser files remain probe-only. They are still skipped with reasons such as `indexeddb_probe_only`, `cache_probe_only`, or `unknown_format`.

Supported commands:

```bash
uv run python -m memsearch.backfill.cli manus-estimate
uv run python -m memsearch.backfill.cli manus-pilot --limit 10 --machine "$(scutil --get ComputerName)" --output .local/manus-api-export
uv run python -m memsearch.backfill.cli manus-export --all --machine "$(scutil --get ComputerName)" --output .local/manus-api-export
uv run python -m memsearch.backfill.cli verify-manus-run .local/manus-api-export/<run_id>
uv run python -m memsearch.backfill.cli scan-secrets .local/manus-api-export/<run_id>
uv run python -m memsearch.backfill.cli manus-promote --run .local/manus-api-export/<run_id> --output .local/manus-api-indexable/<run_id>
uv run python -m memsearch.backfill.cli scan-secrets .local/manus-api-indexable/<run_id>
uv run python -m memsearch.backfill.cli manus-cards --promoted .local/manus-api-indexable/<run_id> --output .local/manus-api-memsearch-cards/<run_id>
uv run python -m memsearch.backfill.cli scan-secrets .local/manus-api-memsearch-cards/<run_id>
```

Weekly freshness command:

```bash
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)" --dry-run --max-tasks 5
```

The weekly Manus route is intentionally conservative. It compares fresh task IDs and `updated_at` values against `.local/source-sync-state/manus.json`. If there is no prior diff state, or if Manus task timestamps are not reliable, it reports a blocked weekly sync and refuses to perform a silent full export. Use `--all` only when a full export has been explicitly approved.

Safety gates:

- Manus API client is read-only. It only calls `GET task.list`, `GET task.listMessages`, and attachment downloads.
- Raw signed attachment URLs are omitted from manifests and rendered Markdown. Sanitised raw message JSON stores `[signed-url-omitted]`.
- Staged exports write under `.local/manus-api-export/<run_id>/`, which is ignored by git.
- Raw staged exports are not MemSearch-ready and must not be indexed.
- The indexable lane is generated separately under `.local/manus-api-indexable/<run_id>/memory/manus_cloud/manus_api/<yyyy-mm>-partN.md`.
- The MemSearch recall lane is generated separately under `.local/manus-api-memsearch-cards/<run_id>/memory/manus_cloud/manus_api/<yyyy-mm>-partN.md`.
- The card lane is the practical MemSearch indexing source. It stores task/session cards with task IDs, Manus URLs, artefact counts, user requests, assistant outcomes, tool hints, and pointers back to the full cleaned transcript.
- Do not index full raw event logs directly unless there is a separate reason. Raw tool payloads create low-value embeddings and the local ONNX provider was too slow for full-transcript ingestion at this scale.
- Weekly automation must keep the same gates: verify run, scan raw run, promote sanitised Markdown, scan promoted output, generate cards, scan cards, then optionally index only when `--index` is explicitly provided.
- Promotion writes `promotion-manifest.json`, `excluded-secrets.json`, `rotation-report.json`, `rotation-report.md`, and `summary.json`.
- `excluded-secrets.json` and rotation reports must not contain raw secret values. They use detector names, severity, task IDs, checksums, and redacted relative paths only.
- If raw scan hits exist, Dom must acknowledge the rotation report with `ROTATE-ACK <run_id>` before any MemSearch indexing.
- First index only into a temporary review collection such as `ms_manus_review_<run_id>_cards_openai`.
- Drop the temporary review collection after approval or rejection.
- Canonical indexing is a re-index from the card Markdown files only. Do not copy vectors from the temporary collection.
- Do not index into the canonical collection until `verify-manus-run`, promoted-output `scan-secrets`, card-output `scan-secrets`, temporary search review, and explicit manual approval all pass.

## Linear route

Linear is a daily freshness source. It fills the gap where session memory knows about past agent work, but not issue comments or execution notes written directly into Linear.

Supported commands:

```bash
uv run python -m memsearch.backfill.cli linear-export --machine "$(scutil --get ComputerName)" --since 2026-06-10T00:00:00Z --output .local/linear-export/run-1
uv run python -m memsearch.backfill.cli linear-cards --machine "$(scutil --get ComputerName)" --run .local/linear-export/run-1 --output .local/linear-cards/run-1
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --dry-run --max-issues 5
```

The automation route uses `LINEAR_API_KEY` against Linear GraphQL. This is the durable route for Codex because the app connector session can expire.

State and output:

- Source state: `.local/source-sync-state/linear.json`.
- Dry-run previews: `.local/source-sync-dry-runs/linear/<run_id>/`.
- Default card output root: `/Users/dominicmonkhouse/Projects/.memsearch/memory/linear`.
- Card anchors include `backfill-agent:linear`, the Linear issue identifier, `source:linear`, and the running machine slug.

Safety gates:

- Linear export is read-only GraphQL.
- Linear cards run `scan_path_for_secrets` before the command reports success.
- Daily sync reads `last_success_at` from state when `--since` is omitted.
- `--dry-run` writes preview artefacts and reports the state update it would make, but does not update state.
- Indexing is opt-in with `--index` and uses the shared `src/memsearch/backfill/indexing.py` wrapper.

## Source freshness policy

Cadence:

- Linear: daily at 06:30 local time.
- Antigravity: daily at 06:40 local time.
- Manus: weekly on Monday at 06:00 local time.

Shared commands:

```bash
uv run python -m memsearch.backfill.cli source-freshness
uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents --machine "$(scutil --get ComputerName)"
```

The scheduler renderer only writes plist files. It does not run `launchctl` and does not install anything. Installing LaunchAgents is an approval-gated future step.

Validated review indexing command:

```bash
memsearch index .local/manus-api-memsearch-cards/<run_id>/memory/manus_cloud/manus_api \
  -c ms_manus_review_<run_id>_cards_openai \
  -p openai \
  -m text-embedding-3-small \
  --force \
  --max-chunk-size 3000
```

Canonical ingestion proof must include:

- Source-side manifest count.
- Generated card task ID count.
- Destination row count after Milvus flush/load.
- Unique Manus task IDs present in indexed content.
- Targeted searches that return expected Manus cards with full cleaned transcript pointers.

Fresh Manus API pilot on 2026-06-04:

- Run ID: `20260604-200322`
- Output: `.local/manus-api-export/20260604-200322/`
- Estimate before pilot: 619 tasks visible through the API: 553 stopped, 49 waiting, 16 error, 1 running.
- Pilot converted: 10 tasks.
- Message events: 655.
- Attachments: 8 found, 8 downloaded.
- Manifest verification: pass.
- Secret scan: `[]`.

Full Manus API export on 2026-06-04:

- Run ID: `20260604-200632`
- Output: `.local/manus-api-export/20260604-200632/`
- Tasks returned: 619.
- Tasks converted: 619.
- Message events: 74,473.
- Attachments: 2,860 found, 2,845 downloaded.
- Task errors: 0.
- Staged size: about 2.9 GB.
- Status: staged only. Do not index.
- Validation result: blocked. The first full run exposed private-key material and service-account-key files inside downloaded Manus artefacts/raw task content. `scan-secrets` returned 79 hits.
- Checksum note: the run also exposed a macOS case-insensitive filename collision between `pasted_content.txt` and `Pasted_content.txt`. The exporter now de-duplicates filenames case-insensitively for future runs.

Indexing status:

- Do not index Manus staged runs into `ms_memsearch_ae2d4f9b` without explicit review approval.
- Temporary review collection indexing is blocked until the full export is re-run with the case-insensitive filename fix and the secret-bearing artefacts are excluded, redacted, or otherwise approved for private storage.
- Run `20260604-200632` must be marked with `WHY-NOT-INDEXED.md` and retained for evidence only. It is not a promotion source.

Full Manus API export on 2026-06-05:

- Run ID: `20260605-092248`
- Output: `.local/manus-api-export/20260605-092248/`
- Tasks returned: 622.
- Tasks converted: 622.
- Message events: 74,556.
- Attachments: 2,862 found, 2,775 downloaded.
- Task errors: 0.
- Verification: `verify-manus-run` passed.
- Raw secret scan: 109 hits in the raw export. Raw export is retained as source-of-truth evidence, not indexed.
- Promotion output: `.local/manus-api-indexable/20260605-092248/`
- Promoted scan: `[]`.
- Card output: `.local/manus-api-memsearch-cards/20260605-092248/`
- Card generation: 63 Markdown files, 622 task cards, 622 unique task IDs.
- Card scan: `[]`.
- Review collection: `ms_manus_review_20260605_092248_cards_openai`
- Review collection provider/model: OpenAI `text-embedding-3-small`.
- Review collection row count: 906 chunks.
- Review coverage: 622 unique Manus task IDs present in indexed content.
- Search checks passed for LinkedIn carousel extraction, Monkhouse image alt text, Manus task ID lookup, and podcast transcript retrieval.
- Canonical/default MemSearch: ingested on 2026-06-06 from `/Users/dominicmonkhouse/Projects/.memsearch/memory/manus-cloud/manus-api/20260605-092248/`.
- Canonical/default collection: `memsearch_chunks`.
- Canonical/default row count after compaction: 1,430 chunks.
- Canonical/default Manus coverage: 901 Manus card chunks, 622 unique Manus task IDs.
- Full cleaned transcript pointers were rewritten to the persistent `.memsearch/memory/manus-cloud/manus-api-full/20260605-092248/` source path. Temporary worktree-source duplicate rows were removed after re-indexing from the persistent `.memsearch/memory` source path.

Temporary review collections created during tuning and safe to remove after checkpoint:

- `ms_manus_review_20260605_092248`
- `ms_manus_review_20260605_092248_cards`
- `ms_manus_review_20260605_092248_chunk12000`
- `ms_manus_review_20260605_092248_compact_3000`
- `ms_manus_review_20260605_092248_memsearch`
- `ms_manus_review_20260605_092248_memsearch_1500`

## Pilot run 2026-06-02

MacBook pilot:

- Output: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/20260602-131937/`
- Converted: 23
- Skipped: 64
- Errors: 0
- Converted products: Claude Code 10, Codex 10, Claude Desktop/Cowork 3

Mac Mini pilot:

- Output copied locally to: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/20260602-131937-mini/`
- Converted: 22
- Skipped: 60
- Errors: 0
- Converted products: Claude Code 10, Codex 10, Claude Desktop/Cowork 2

Secret scan:

- Filtered scan returned `hits 0` across both pilot runs.
- Redaction now removes `computer:///sessions/...` links and `*-service-account-key.json` filenames from rendered markdown.

Indexing blocker:

- Do not index pilot or production imported chats yet.
- `memsearch stats` currently reports an index, but searching `backfill-agent:codex` returns `claude-config` memory rather than `.memsearch/memory/historical-sessions`.
- Searching with `--source-prefix /Users/dominicmonkhouse/Projects/.memsearch/memory/historical-sessions` returns no results.
- Production indexing remains blocked until the target Memsearch collection is confirmed to contain existing historical-session chunks.
