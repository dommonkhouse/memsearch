<!--
MON-316 capped Graphiti relationship seed batch 013 source map.
Reviewed on 2026-06-14.
-->

# Source files reviewed for capped batch 013

- docs/architecture.md
- docs/cli.md
- docs/backfill-chat-sources.md

# Relationship extraction notes

- Progressive disclosure relationships came from architecture and CLI sections describing L1 search, L2 expand, L3 transcript, session anchors, chunk hashes, and transcript paths.
- Derived index rebuild relationships came from architecture and CLI sections describing Markdown as source of truth, Milvus as derived storage, content-hash dedup, stale cleanup, and reset/re-index safety.
- Optional Graphiti sidecar CLI relationships came from CLI sections describing graph-status, graph-index, graph-search, search --include-graph, and vector-only fallback.
- Source sync approval boundary relationships came from backfill source documentation describing Linear dry-runs, Manus weekly sync, secret scans, review collections, and canonical card indexing approval.

# Explicit exclusions

- No full .memsearch/memory ingestion was performed.
- No raw Manus exports, transcripts, caches, or imported session folders were ingested.
- Runtime manifest and checkpoint files remain local and are not committed.
