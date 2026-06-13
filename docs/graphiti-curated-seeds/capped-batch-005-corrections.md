<!--
MON-316 capped Graphiti relationship seed batch 005 corrective reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-005-sources.md
-->

# Installation profile correction relationships

ONNX is the default local embedding profile for MemSearch.
ONNX is a local embedding profile.
ONNX requires no API key.
MemSearch Windows guidance says Milvus Lite does not provide Windows binaries.
Windows should not use native Milvus Lite for MemSearch.
Windows alternatives are Milvus Server via Docker, Zilliz Cloud, and WSL2.
Milvus Server via Docker works as a Windows alternative to native Milvus Lite.
Zilliz Cloud works as a Windows alternative to native Milvus Lite.
WSL2 works as a Windows alternative when local Milvus Lite workflow is required.

# Recovery wording relationships

Dimension mismatch recovery runs `memsearch reset --yes`.
Dimension mismatch recovery runs `memsearch index`.
Dimension mismatch recovery resets only the vector index.
Dimension mismatch recovery keeps Markdown as the source of truth.
Changing the embedding provider/model requires `memsearch index --force`.

# Troubleshooting first-step relationships

Missing search results first step is `memsearch stats`.
Missing search results second step is `memsearch search`.
If `memsearch stats` shows zero or unexpectedly low count, rebuild the index.
Queries that are too short or vague can return weak search results.
Stale index state can cause missing search results.
