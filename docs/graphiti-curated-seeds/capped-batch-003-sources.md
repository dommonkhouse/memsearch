# Batch 003 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti ingest expansion.

## Source safety decisions

- `docs/source-freshness-automation.md`: safe to distil, unsafe for direct ingestion. It is current operator documentation, but command examples and scheduler install snippets should not become general graph facts.
- `docs/backfill-chat-sources.md`: safe to distil, unsafe for direct ingestion. It includes current source-sync safety policy and also historical pilot/export numbers, blocked runs, and local paths that are too noisy for direct graph ingestion.

## Statement evidence

- Statement: Linear source sync runs daily at 06:30 local time.
  Evidence: `docs/source-freshness-automation.md:5-10`; `docs/backfill-chat-sources.md:118-123`.
- Statement: Manus source sync runs weekly on Monday at 06:00 local time.
  Evidence: `docs/source-freshness-automation.md:5-10`; `docs/backfill-chat-sources.md:118-123`.
- Statement: Linear freshness state lives in `.local/source-sync-state/linear.json`.
  Evidence: `docs/source-freshness-automation.md:12-27`; `docs/backfill-chat-sources.md:103-108`.
- Statement: Manus freshness state lives in `.local/source-sync-state/manus.json`.
  Evidence: `docs/source-freshness-automation.md:12-27`; `docs/backfill-chat-sources.md:62-68`.
- Statement: Source freshness reports show state presence, last success, last failure, generated Markdown card counts, next expected run, and proof-search commands.
  Evidence: `docs/source-freshness-automation.md:87-99`.
- Statement: Source freshness proof searches are previewed by default.
  Evidence: `docs/source-freshness-automation.md:87-99`.
- Statement: Source freshness runs proof searches only when `--run-proof` is provided.
  Evidence: `docs/source-freshness-automation.md:87-99`.
- Statement: Linear source sync uses read-only GraphQL.
  Evidence: `docs/backfill-chat-sources.md:89-117`.
- Statement: Linear source sync reads `last_success_at` from `.local/source-sync-state/linear.json` when `--since` is omitted.
  Evidence: `docs/source-freshness-automation.md:45-57`; `docs/backfill-chat-sources.md:110-117`.
- Statement: Linear source sync writes dry-run previews under `.local/source-sync-dry-runs/linear/`.
  Evidence: `docs/backfill-chat-sources.md:103-117`.
- Statement: Linear card anchors include `backfill-agent:linear`.
  Evidence: `docs/backfill-chat-sources.md:103-109`.
- Statement: Linear indexing is opt-in with `--index`.
  Evidence: `docs/source-freshness-automation.md:53-57`; `docs/backfill-chat-sources.md:110-117`.
- Statement: Manus source sync uses `task.list` for task metadata.
  Evidence: `docs/backfill-chat-sources.md:38-46`.
- Statement: Manus source sync uses `task.listMessages` for task event history.
  Evidence: `docs/backfill-chat-sources.md:38-46`.
- Statement: Manus source sync exports changed tasks only when reliable diff state exists.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:62-68`.
- Statement: Manus raw exports must not be indexed.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus raw exports are not MemSearch-ready.
  Evidence: `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus card lane is the practical MemSearch indexing source.
  Evidence: `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus card lane stores task IDs, Manus URLs, artefact counts, user requests, assistant outcomes, tool hints, and pointers to full cleaned transcripts.
  Evidence: `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus source sync must verify the run before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus source sync must scan raw output before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus source sync must scan promoted output before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus source sync must scan cards before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus indexing is opt-in with `--index`.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Source freshness cadence links Linear to a daily run.
  Evidence: `docs/source-freshness-automation.md:5-10`; `docs/backfill-chat-sources.md:118-123`.
- Statement: Source freshness cadence links Manus to a weekly run.
  Evidence: `docs/source-freshness-automation.md:5-10`; `docs/backfill-chat-sources.md:118-123`.
- Statement: Linear source sync uses `last_success_at` for incremental freshness windows.
  Evidence: `docs/source-freshness-automation.md:45-57`; `docs/backfill-chat-sources.md:110-117`.
- Statement: Linear source sync indexing is opt-in.
  Evidence: `docs/source-freshness-automation.md:53-57`; `docs/backfill-chat-sources.md:110-117`.
- Statement: Raw Manus exports must not be indexed directly.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus secret scan gates include scan raw output before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus secret scan gates include scan promoted output before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
- Statement: Manus secret scan gates include scan cards before indexing.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-88`.
