<!--
MON-316 capped Graphiti relationship seed batch 012 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-012-sources.md
-->

# Zero-config backend choice correction relationships

Zero-config backend choice answer includes local embeddings, no API key, Milvus Lite, Milvus Server, Zilliz Cloud, and production.
Zero-config local setup uses local embeddings.
Zero-config local setup needs no API key.
Zilliz Cloud is the production managed backend.

# Agent loop recall think remember correction relationships

The memsearch agent loop answer includes Recall, Think, Remember, daily markdown, LLM, and re-index.
Recall searches past memories.
Think calls the LLM with memory context.
Remember writes the exchange to daily markdown.
After Remember, memsearch re-indexes daily markdown.

# Python API per-user isolation correction relationships

Python API per-user isolation answer includes per-user isolation, paths, collection, milvus_uri, separate database, and never see each other's data.
Different users can use different paths.
Different users can use different collection names.
Different users can use different milvus_uri values.
Separate database files are the strongest per-user isolation option.
With per-user isolation, users never see each other's data.

# Troubleshooting reset rebuild correction relationships

Troubleshooting reset rebuild answer includes memsearch stats, memsearch reset --yes, memsearch index . --force, source markdown, dimension mismatch, and embedding provider/model.
Use memsearch stats before rebuilding missing search results.
Use memsearch index . --force when the index is zero, low, stale, or irrelevant.
Use memsearch reset --yes for dimension mismatch.
After memsearch reset --yes, run memsearch index . --force.
Resetting drops the vector index but keeps source markdown.
