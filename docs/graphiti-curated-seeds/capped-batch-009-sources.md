# Batch 009 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti source-freshness relationship tuning.

## Source safety decisions

- `docs/source-freshness-automation.md`: safe to distil, unsafe for direct ingestion. It contains operator commands and recovery instructions; Batch 009 only needs cadence, state, indexing, scheduler, and proof-search relationships.
- `docs/backfill-chat-sources.md`: safe to distil, unsafe for direct ingestion. It contains full Manus export history and operational details; Batch 009 only needs the Linear route, Manus route, source freshness policy, and safety gates.

## Statement evidence

- Statement: Linear runs daily at 06:30 and Manus runs weekly on Monday at 06:00.
  Evidence: `docs/source-freshness-automation.md:5-10`; `docs/backfill-chat-sources.md:118-123`.
- Statement: Linear source sync reads `last_success_at` from `.local/source-sync-state/linear.json` when `--since` is omitted.
  Evidence: `docs/source-freshness-automation.md:45-57`; `docs/backfill-chat-sources.md:103-116`.
- Statement: Linear dry runs write preview artefacts, do not update state, and indexing is opt-in with `--index`.
  Evidence: `docs/source-freshness-automation.md:29-57`; `docs/backfill-chat-sources.md:110-116`.
- Statement: Linear cards run `scan_path_for_secrets` before success and can index into `memsearch_chunks` only with explicit `--index --collection memsearch_chunks`.
  Evidence: `docs/source-freshness-automation.md:53-57`; `docs/backfill-chat-sources.md:110-116`.
- Statement: Manus dry run blocks without prior diff state unless `--all` is explicitly requested.
  Evidence: `docs/source-freshness-automation.md:37-43`; `docs/backfill-chat-sources.md:62-68`.
- Statement: Manus source sync sequence is fetch task list, compare task IDs and `updated_at`, export changed tasks, verify, scan raw, promote, scan promoted, generate cards, scan cards, update state, and index only with `--index`.
  Evidence: `docs/source-freshness-automation.md:71-85`; `docs/backfill-chat-sources.md:70-87`.
- Statement: Raw Manus exports are not MemSearch-ready and must not be indexed.
  Evidence: `docs/source-freshness-automation.md:85`; `docs/backfill-chat-sources.md:74-80`.
- Statement: Scheduler rendering writes daily and weekly LaunchAgent plist files and logs under `.local/source-sync-logs/`.
  Evidence: `docs/source-freshness-automation.md:101-120`; `docs/backfill-chat-sources.md:125-132`.
- Statement: Scheduler rendering does not install LaunchAgents, and installation is approval-gated through future `launchctl bootstrap` commands.
  Evidence: `docs/source-freshness-automation.md:120-127`; `docs/backfill-chat-sources.md:125-132`.
- Statement: `source-freshness` reports state presence, last success, last failure, generated Markdown card counts, next expected run, and proof-search commands.
  Evidence: `docs/source-freshness-automation.md:87-99`.
