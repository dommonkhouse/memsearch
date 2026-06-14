<!--
MON-316 capped Graphiti relationship seed batch 012 anchor correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-012-sources.md
-->

# Backend choice anchor relationships

The zero-config backend choice answer must include no API key.
The zero-config backend choice answer must include production.
Local embeddings require no API key.
Zilliz Cloud is the production backend.

# Per-user isolation anchor relationships

The Python API per-user isolation answer must include separate database.
Separate database isolation uses different milvus_uri values.
Separate database files provide strongest isolation.

# Reset rebuild command anchor relationships

The troubleshooting reset rebuild answer must include memsearch reset --yes.
The troubleshooting reset rebuild answer must include memsearch index . --force.
Use memsearch reset --yes before rebuilding dimension mismatch.
Use memsearch index . --force after reset or stale indexing.
