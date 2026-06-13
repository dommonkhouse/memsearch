<!--
MON-316 capped Graphiti relationship seed batch 009 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-009-sources.md
-->

# Source freshness retrieval correction relationships

When asked how source-sync linear uses `last_success_at`, dry-run, and optional indexing, answer with Linear source sync.
Linear source sync uses `last_success_at` for incremental freshness.
Linear source sync writes dry-run previews.
Linear source sync only indexes when `--index` is explicit.
Linear source sync can write to `memsearch_chunks`.
Linear source sync runs `scan_path_for_secrets`.

When asked what gates happen before Manus cards can be indexed into MemSearch, answer with the Manus weekly safety sequence.
The Manus weekly safety sequence is: verify run, scan raw run, promote sanitised Markdown, scan promoted output, generate cards, scan cards, then index only with `--index`.

When asked what `source-freshness` reports and how proof searches work, answer with the source freshness report.
The source freshness report includes state presence, last success, last failure, generated Markdown card counts, and next expected run.
The source freshness report includes state presence.
The source freshness report includes last success.
The source freshness report includes last failure.
The source freshness report includes generated Markdown card counts.
The source freshness report includes next expected run.
The source freshness report previews `proof-search` commands by default.
The source freshness report runs proof searches only with `--run-proof`.
