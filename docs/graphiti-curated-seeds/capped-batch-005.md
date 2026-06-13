<!--
MON-316 capped Graphiti relationship seed batch 005.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-005-sources.md
-->

# Installation and backend relationships

MemSearch local embedding profile uses ONNX by default.
ONNX embedding profile needs no API key.
OpenAI-compatible embedding providers need provider API keys.
OpenAI embedding provider uses `OPENAI_API_KEY`.
Google embedding provider uses `GOOGLE_API_KEY`.
Voyage embedding provider uses `VOYAGE_API_KEY`.
Milvus Lite is the default local backend.
Milvus Lite is zero config and single file.
Zilliz Cloud is the recommended managed backend.
Zilliz Cloud supports concurrent access and real-time indexing.
Milvus Server is the self-hosted Docker backend for advanced users.
Windows should use Milvus Server, Zilliz Cloud, or WSL2 instead of native Milvus Lite.

# Recovery and troubleshooting relationships

Dimension mismatch means the current embedding provider/model produces a different vector size from the existing Milvus collection.
Dimension mismatch recovery resets the vector index.
Dimension mismatch recovery re-indexes Markdown files.
Changing embedding provider/model requires re-indexing.
Markdown is the source of truth during reset and rebuild.
Milvus is a rebuildable derived index.
Missing search results should start with `memsearch stats`.
Missing search results should inspect actual results with `memsearch search`.
If stats are zero or unexpectedly low, rebuild the index.
Search results can be stale when the index needs re-indexing.
Search results can be weak when a query is too short or vague.
Search results can be wrong when the embedding provider/model changed after collection creation.
Remote Milvus stats may lag after upserts.
Search results are the better source of truth for whether content is searchable right now.

# Progressive disclosure and Codex mode relationships

Progressive disclosure starts with L1 search.
L1 search uses `memsearch search`.
Progressive disclosure continues with L2 expand.
L2 expand uses `memsearch expand`.
L2 expand returns the full markdown section around a chunk.
Progressive disclosure can continue with L3 transcript.
L3 transcript uses `memsearch transcript` or plugin transcript parsers.
L3 transcript returns original conversation turns.
Codex Server mode starts `memsearch watch`.
Codex Milvus Lite mode runs a one-time index.
Codex Milvus Lite mode skips `memsearch watch` because Milvus Lite uses a file-level lock.
For real-time indexing without Milvus Lite lock issues, use Milvus Server or Zilliz Cloud.
