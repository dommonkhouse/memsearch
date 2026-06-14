<!--
MON-316 capped Graphiti relationship seed batch 013.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-013-sources.md
-->

# Progressive disclosure anchor bridge relationships

MemSearch progressive disclosure has three levels: L1 search, L2 expand, and L3 transcript.
L1 search returns chunk snippets from the shared vector index.
L2 expand uses a chunk hash to read the full heading section from the original source markdown file.
Session anchors inside source markdown connect L2 expand to L3 transcript.
Session anchors include session ID, turn ID, and transcript path.
L3 transcript reads the original conversation from platform-specific transcript files.
The progressive disclosure bridge lets agents start with small snippets and drill down only when more context is needed.

# Derived index rebuild safety relationships

Markdown is the MemSearch source of truth.
Milvus is a derived vector index.
MemSearch chunk IDs include source path, line range, content hash, and embedding model.
Content-hash dedup means unchanged chunks are skipped during re-indexing.
Stale cleanup removes vector chunks for source files that no longer exist.
Rebuilding the index is safe when the source markdown is still present.
Resetting or rebuilding the vector index does not delete the source markdown.

# Optional Graphiti sidecar CLI relationships

Graphiti is an optional graph sidecar for relationship-style recall.
Markdown remains the source of truth when Graphiti is enabled.
Graphiti stores derived episodes and relationships, not canonical memory.
memsearch graph-status checks the configured Graphiti MCP endpoint.
memsearch graph-index queues curated markdown sections into Graphiti as episodes.
memsearch graph-search searches Graphiti facts and nodes.
memsearch search --include-graph blends vector results with the curated Graphiti sidecar.
If Graphiti is unavailable, memsearch search returns vector results only.

# Source sync approval boundary relationships

Linear source sync is a daily freshness source that uses read-only GraphQL.
Linear dry-run previews show what would sync without updating state.
Manus source sync is weekly and intentionally conservative.
Manus sync refuses silent full export when prior diff state is missing or timestamps are unreliable.
Manus raw exports are staged evidence and must not be indexed directly.
scan-secrets gates raw Manus output, promoted output, and card output.
Canonical Manus indexing happens from reviewed card markdown only.
Canonical indexing requires approval after verification, secret scans, and temporary search review.
