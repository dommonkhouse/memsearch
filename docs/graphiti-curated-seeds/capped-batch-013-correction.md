<!--
MON-316 capped Graphiti relationship seed batch 013 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-013-sources.md
-->

# Progressive disclosure anchor bridge correction relationships

The progressive disclosure anchor bridge answer includes L1 search, L2 expand, L3 transcript, session anchors, transcript path, and original conversation.
L1 search returns small chunk snippets.
L2 expand reads the full heading section from source markdown.
Session anchors expose session ID, turn ID, and transcript path.
L3 transcript uses the transcript path to recover the original conversation.

# Derived index rebuild safety correction relationships

The derived index rebuild safety answer includes Markdown, source of truth, Milvus, derived index, content-hash dedup, and rebuild.
Markdown is the source of truth.
Milvus is the derived index.
Content-hash dedup skips unchanged chunks during rebuild.
Reset and rebuild are safe only because source markdown remains present.
Milvus is not the source of truth.

# Graphiti sidecar CLI routing correction relationships

The Graphiti sidecar CLI routing answer includes graph-status, graph-index, graph-search, include-graph, optional graph sidecar, and Markdown remains the source of truth.
graph-status checks the Graphiti MCP endpoint.
graph-index queues curated markdown sections into Graphiti.
graph-search searches Graphiti facts and nodes.
search --include-graph queries Graphiti as an optional sidecar.
Default search remains vector-first and falls back to vector results if Graphiti fails.

# Source sync approval boundary correction relationships

The source sync approval boundary answer includes Linear, Manus, dry-run, scan-secrets, approval, and canonical indexing.
Linear sync uses read-only GraphQL and supports dry-run previews.
Manus sync requires verification and scan-secrets gates.
Manus raw exports must not be indexed directly.
Canonical indexing uses reviewed card markdown only after approval.
Silent full export is not allowed.
