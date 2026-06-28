# Source freshness automation

This guide covers the MemSearch freshness layer for Linear, Antigravity, and Manus. It does not install schedulers, deploy services, or change canonical indexing by default.

## Cadence

- Linear runs daily at 06:30 local time.
- Antigravity runs daily at 06:40 local time.
- Manus runs weekly on Monday at 06:00 local time.

Linear changes more often and is lightweight to query. Antigravity/Gemini sessions default to 30-day retention, so they need daily capture. Manus exports are heavier, include attachments, and require stricter promotion and secret-scan gates.

## State

State files live under:

```text
.local/source-sync-state/
```

Expected files:

```text
.local/source-sync-state/linear.json
.local/source-sync-state/antigravity.json
.local/source-sync-state/manus.json
```

These are local runtime artefacts and stay ignored by git.

## One-off dry runs

Linear:

```bash
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --dry-run --max-issues 5
```

Manus:

```bash
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)" --dry-run --max-tasks 5
```

The Manus dry run will report `blocked` until prior diff state exists, unless a full export is explicitly requested with `--all`.

Antigravity:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity --machine "$(scutil --get ComputerName)" --dry-run --max-sessions 5
```

The Antigravity dry run discovers `~/.gemini/tmp/*/chats/*.json` and `~/.gemini/antigravity-cli/brain/*/.system_generated/logs/transcript.jsonl`, reports changed sessions, and does not write `.local/source-sync-state/antigravity.json`.

## Daily Linear command

```bash
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)"
```

Use `--since <timestamp>` for a one-off backfill window. Without `--since`, the command reads `last_success_at` from `.local/source-sync-state/linear.json`.

Indexing is opt-in:

```bash
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --index --collection memsearch_chunks
```

## Daily Antigravity command

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity --machine "$(scutil --get ComputerName)"
```

Without `--index`, the daily run writes compact Gemini session cards under `/Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/`, scans them for secrets, and updates `.local/source-sync-state/antigravity.json`.

First-run review collection:

```bash
uv run memsearch index /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli \
  -c ms_antigravity_review_<run_id>_cards_openai \
  -p openai \
  -m text-embedding-3-small
```

Review indexing is temporary. Canonical indexing waits for card inspection, proof searches, and explicit approval.

OpenBrain/Graphiti uses the same reviewed compact cards as its first-party Antigravity source. Do not ingest raw Gemini JSON. After review, queue only the generated card Markdown:

```bash
uv run memsearch graph-index-curated /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli/<month>.md --dry-run
uv run memsearch graph-index-curated /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli/<month>.md --limit 5
```

## Weekly Manus command

```bash
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)"
```

Use `--all` only when a full Manus export has been explicitly approved:

```bash
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)" --all
```

The Manus sync sequence is:

1. Fetch task list.
2. Compare task IDs and `updated_at` values with prior state.
3. Export changed tasks only when reliable diff state exists.
4. Verify the run.
5. Scan the raw run.
6. Promote sanitised Markdown.
7. Scan promoted output.
8. Generate cards.
9. Scan cards.
10. Update state.
11. Index only when `--index` is explicitly provided.

Raw Manus exports must not be indexed.

## Freshness report

```bash
uv run python -m memsearch.backfill.cli source-freshness
```

The report shows state presence, last success, last failure, generated Markdown card counts, next expected run, and proof-search commands. Proof searches are previewed by default.

To run proof searches:

```bash
uv run python -m memsearch.backfill.cli source-freshness --run-proof
```

## Daily proof job

After the 06:30 Linear sync and 06:40 Antigravity sync, `com.memsearch.source-freshness-proof` runs at 06:45 and executes:

```bash
uv run python -m memsearch.backfill.cli source-freshness --run-proof
```

The job prefers `/Volumes/SSD/graphiti-mon316/logs/source-freshness-proof.log` on the Mini and falls back to `~/Library/Logs/graphiti-mon316/source-freshness-proof.log` when launchd cannot write to the external SSD.

## Scheduler rendering

```bash
uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents --machine "$(scutil --get ComputerName)"
```

This writes:

```text
.local/launchagents/com.memsearch.daily-linear-sync.plist
.local/launchagents/com.memsearch.daily-antigravity-sync.plist
.local/launchagents/com.memsearch.weekly-manus-sync.plist
```

The Antigravity scheduler output path is `.local/launchagents/com.memsearch.daily-antigravity-sync.plist`.

On Dominic's Mac Mini it also renders:

```text
.local/launchagents/com.monkhouse.graphiti-mon316-watchdog.plist
.local/launchagents/com.monkhouse.graphiti-mon316-backup.plist
.local/launchagents/com.memsearch.source-freshness-proof.plist
.local/launchagents/com.memsearch.graphiti-candidate-report.plist
```

It also writes logs under:

```text
.local/source-sync-logs/
```

Do not install these plists without explicit approval.

Future install commands, approval-gated:

```bash
launchctl bootstrap "gui/$(id -u)" .local/launchagents/com.memsearch.daily-linear-sync.plist
launchctl bootstrap "gui/$(id -u)" .local/launchagents/com.memsearch.daily-antigravity-sync.plist
launchctl bootstrap "gui/$(id -u)" .local/launchagents/com.memsearch.weekly-manus-sync.plist
```

## Recovery

- If Linear fails, check `.local/source-sync-state/linear.json` and rerun with an explicit `--since` timestamp.
- If Antigravity fails, check `.local/source-sync-state/antigravity.json` and rerun the dry-run command before a non-indexing daily command.
- If Manus reports missing diff state, run a dry run with `--all` first and review the planned full export.
- If any secret scan fails, do not index. Inspect the reported file path, rotate affected credentials where needed, and rerun the relevant promotion/card step after the source is safe.
- If scheduler output looks wrong, delete the rendered `.local/launchagents/*.plist` files and render again. Do not edit installed LaunchAgents in place.
