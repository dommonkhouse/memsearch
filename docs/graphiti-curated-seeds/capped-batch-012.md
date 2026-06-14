<!--
MON-316 capped Graphiti relationship seed batch 012.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-012-sources.md
-->

# Zero-config backend choice relationships

Zero-config quick start uses local embeddings and Milvus Lite.
Zero-config quick start requires no API key.
Milvus Lite is the default backend for personal use, single-agent setups, prototyping, and development.
Milvus Server is for self-hosted multi-agent or team environments.
Zilliz Cloud is for production, fully managed Milvus, real-time indexing, and teams that do not want Docker operations.
Windows should use Milvus Server, Zilliz Cloud, or WSL2 instead of native Milvus Lite.
Users can switch from Milvus Lite to Zilliz Cloud by changing config and rebuilding from source markdown.

# Agent loop relationships

The memsearch agent loop is recall, think, remember.
Recall searches past memories with mem.search.
Think calls the LLM with relevant memory context.
Remember saves the exchange to a daily markdown log.
After remember, memsearch re-indexes the daily markdown log.
OpenAI, Anthropic Claude, and Ollama examples use the same recall-think-remember structure.

# Python API per-user isolation relationships

The Python API supports per-user isolation with paths, collection, and milvus_uri.
Directory plus collection isolation is the recommended per-user isolation option.
Different users can use different markdown paths.
Different users can use different Milvus collection names.
Separate Milvus Lite database files through milvus_uri provide the strongest isolation.
With per-user isolation, users never see each other's data.

# Troubleshooting reset rebuild relationships

When search returns no results, start with memsearch stats.
If memsearch stats is zero or unexpectedly low, run memsearch index . --force.
If search is irrelevant, stale, or too vague, re-index and check the embedding provider/model.
Dimension mismatch means the collection was created with a different embedding dimension from the current provider/model.
Dimension mismatch is fixed with memsearch reset --yes followed by memsearch index .
memsearch reset --yes drops the vector index but does not delete source markdown.
Rebuilding is safe when source markdown files are still present.
