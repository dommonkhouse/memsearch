<!--
MON-316 capped Graphiti relationship seed batch 013 anchor correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-013-sources.md
-->

# Progressive disclosure anchor relationships

The progressive disclosure answer must include session anchors.
The progressive disclosure answer must include transcript path.
Session anchors connect L2 expand to L3 transcript.
L3 transcript recovers the original conversation.

# Derived index anchor relationships

The rebuild safety answer must include content-hash dedup.
Content-hash dedup is part of safe re-indexing.
Milvus is a derived index.
Markdown is the source of truth.

# Graphiti CLI anchor relationships

The Graphiti sidecar answer must include include-graph.
search --include-graph uses the optional graph sidecar.
graph-index queues curated markdown sections.
graph-search searches facts and nodes.

# Source sync approval anchor relationships

The source sync answer must include canonical indexing.
Canonical indexing happens from reviewed card markdown only.
Approval is required before canonical indexing.
scan-secrets gates source sync before indexing.
