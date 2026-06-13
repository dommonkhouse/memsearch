<!--
MON-316 capped Graphiti relationship seed batch 003.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-003-sources.md
-->

# Source freshness cadence relationships

Linear source sync runs daily at 06:30 local time.
Manus source sync runs weekly on Monday at 06:00 local time.
Linear freshness state lives in `.local/source-sync-state/linear.json`.
Manus freshness state lives in `.local/source-sync-state/manus.json`.
Source freshness reports show state presence, last success, last failure, generated Markdown card counts, next expected run, and proof-search commands.
Source freshness proof searches are previewed by default.
Source freshness runs proof searches only when `--run-proof` is provided.

# Linear source sync relationships

Linear source sync uses read-only GraphQL.
Linear source sync reads `last_success_at` from `.local/source-sync-state/linear.json` when `--since` is omitted.
Linear source sync writes dry-run previews under `.local/source-sync-dry-runs/linear/`.
Linear card anchors include `backfill-agent:linear`.
Linear indexing is opt-in with `--index`.

# Manus source sync safety relationships

Manus source sync uses `task.list` for task metadata.
Manus source sync uses `task.listMessages` for task event history.
Manus source sync exports changed tasks only when reliable diff state exists.
Manus raw exports must not be indexed.
Manus raw exports are not MemSearch-ready.
Manus card lane is the practical MemSearch indexing source.
Manus card lane stores task IDs, Manus URLs, artefact counts, user requests, assistant outcomes, tool hints, and pointers to full cleaned transcripts.
Manus source sync must verify the run before indexing.
Manus source sync must scan raw output before indexing.
Manus source sync must scan promoted output before indexing.
Manus source sync must scan cards before indexing.
Manus indexing is opt-in with `--index`.

# Source freshness summary relationships

Source freshness cadence links Linear to a daily run.
Source freshness cadence links Manus to a weekly run.
Linear source sync uses `last_success_at` for incremental freshness windows.
Linear source sync indexing is opt-in.
Raw Manus exports must not be indexed directly.
Manus secret scan gates include scan raw output before indexing.
Manus secret scan gates include scan promoted output before indexing.
Manus secret scan gates include scan cards before indexing.
