<!--
MON-316 capped Graphiti relationship seed batch 009.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-009-sources.md
-->

# Linear source sync indexing relationships

Linear source sync runs daily at 06:30 local time.
Linear source sync reads `last_success_at` from `.local/source-sync-state/linear.json` when `--since` is omitted.
Linear source sync writes dry-run previews under `.local/source-sync-dry-runs/linear/`.
Linear source sync uses read-only Linear GraphQL with `LINEAR_API_KEY`.
Linear cards run `scan_path_for_secrets` before the command reports success.
Linear source sync indexing is opt-in with `--index`.
Linear source sync can index into `memsearch_chunks` when `--index --collection memsearch_chunks` is explicitly provided.
Linear source sync does not update state during `--dry-run`.

# Manus weekly safety sequence relationships

Manus source sync runs weekly on Monday at 06:00 local time.
Manus dry-run reports blocked until prior diff state exists unless `--all` is explicitly requested.
Manus source sync fetches the task list.
Manus source sync compares task IDs and `updated_at` values with prior state.
Manus source sync exports changed tasks only when reliable diff state exists.
Manus source sync must verify run before indexing.
Manus source sync must scan raw run before indexing.
Manus source sync must promote sanitised Markdown before indexing.
Manus source sync must scan promoted output before indexing.
Manus source sync must generate cards before indexing.
Manus source sync must scan cards before indexing.
Manus source sync indexes only when `--index` is explicitly provided.
Raw Manus exports must not be indexed.

# Scheduler render approval relationships

`scheduler-render` writes LaunchAgent plist files under `.local/launchagents`.
`scheduler-render` writes `com.memsearch.daily-linear-sync.plist`.
`scheduler-render` writes `com.memsearch.weekly-manus-sync.plist`.
`scheduler-render` writes logs under `.local/source-sync-logs/`.
`scheduler-render` does not install LaunchAgents automatically.
Installing source freshness LaunchAgents is approval-gated.
Future LaunchAgent installation uses `launchctl bootstrap`.

# Source freshness report relationships

`source-freshness` reports source state presence.
`source-freshness` reports last success.
`source-freshness` reports last failure.
`source-freshness` reports generated Markdown card counts.
`source-freshness` reports the next expected run.
`source-freshness` previews proof-search commands by default.
`source-freshness --run-proof` runs proof searches.
