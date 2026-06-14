# Capped batch 017 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti Superpowers-plan tuning.

## Reviewed source files

- `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md`: safe to distil, unsafe for direct ingestion. It contains durable Graphiti sidecar, backend, and non-default boundaries mixed with historical implementation tasks.
- `docs/superpowers/plans/2026-06-13-graphiti-capped-ingest-expansion.md`: safe to distil, unsafe for direct ingestion. It contains durable capped-ingest safety rules and rollback details mixed with batch-001 execution tasks.
- `docs/superpowers/plans/2026-06-01-memsearch-chat-backfill.md`: safe to distil, unsafe for direct ingestion. It contains durable backfill architecture and source-of-truth rules mixed with large source inventories and implementation task lists.
- `docs/superpowers/plans/2026-06-06-manus-memsearch-closeout.md`: safe to distil, unsafe for direct ingestion. It contains durable Manus three-lane recall and canonical-ingestion boundaries mixed with closeout task details.
- `docs/superpowers/plans/2026-06-11-memory-source-freshness-automation.md`: safe to distil, unsafe for direct ingestion. It contains durable Linear/Manus scheduling and source-card boundaries mixed with implementation tasks.

## Evidence statements

- Statement: Graphiti was planned as an optional derived knowledge-graph layer that does not replace Markdown, Milvus, or memory recall.
  Evidence: `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:5-7`.
- Statement: Markdown remains canonical, Milvus remains primary, and Graphiti is an explicit second-stage recall path until proven.
  Evidence: `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:45-49`.
- Statement: The first Graphiti version exposes explicit CLI graph commands and avoids automatic prompt injection until the pilot proves useful.
  Evidence: `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:7`; `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:45-53`.
- Statement: FalkorDB stayed first while Kuzu was deferred because of archive status and Graphiti Kuzu issue churn.
  Evidence: `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:24-29`; `docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md:51`.
- Statement: Capped ingest uses group `ms_memsearch_active_curated_v1`, manifest `.memsearch/graphiti-curated-manifest.json`, and dry-run/cap/checkpoint/evaluation/rollback controls.
  Evidence: `docs/superpowers/plans/2026-06-13-graphiti-capped-ingest-expansion.md:5-9`; `docs/superpowers/plans/2026-06-13-graphiti-capped-ingest-expansion.md:35-45`.
- Statement: Capped ingest rollback clears only the curated group and restores the manifest checkpoint.
  Evidence: `docs/superpowers/plans/2026-06-13-graphiti-capped-ingest-expansion.md:82-112`.
- Statement: Chat backfill uses source-normalisation, canonical markdown grouped by machine/source/month, repeatable manifests, and `memsearch index`.
  Evidence: `docs/superpowers/plans/2026-06-01-memsearch-chat-backfill.md:5-8`; `docs/superpowers/plans/2026-06-01-memsearch-chat-backfill.md:64-75`.
- Statement: Chat backfill treats generated markdown and manifests as source of truth while Milvus remains derived.
  Evidence: `docs/superpowers/plans/2026-06-01-memsearch-chat-backfill.md:7`.
- Statement: Manus closeout uses raw export, sanitised full Markdown, and compact session cards as separate lanes.
  Evidence: `docs/superpowers/plans/2026-06-06-manus-memsearch-closeout.md:5-8`.
- Statement: Canonical Manus ingestion must use compact cards, not raw event logs, because ONNX full-transcript embedding was too slow and raw payloads made low-value embeddings.
  Evidence: `docs/superpowers/plans/2026-06-06-manus-memsearch-closeout.md:7`; `docs/superpowers/plans/2026-06-06-manus-memsearch-closeout.md:23-28`.
- Statement: Source freshness refreshes Manus weekly and Linear daily while keeping Markdown canonical and Milvus rebuildable.
  Evidence: `docs/superpowers/plans/2026-06-11-memory-source-freshness-automation.md:5-8`.
- Statement: Source freshness writes source cards into `.memsearch/memory/`, keeps scheduler definitions dry-run until approval, uses `LINEAR_API_KEY`, and requires Manus client-side diff with refusal of silent full export.
  Evidence: `docs/superpowers/plans/2026-06-11-memory-source-freshness-automation.md:28-43`; `docs/superpowers/plans/2026-06-11-memory-source-freshness-automation.md:92-102`.
