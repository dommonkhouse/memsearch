# Batch 012 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti getting-started, Python API, FAQ, and troubleshooting relationship tuning.

## Source safety decisions

- `docs/getting-started.md`: safe to distil, unsafe for direct ingestion. It contains long setup, config, and agent examples; Batch 012 only needs zero-config backend choice, recall-think-remember, API key, rebuild, and multi-developer relationships.
- `docs/python-api.md`: safe to distil, unsafe for direct ingestion. It contains API signatures and full code examples; Batch 012 only needs MemSearch method and per-user isolation relationships.
- `docs/faq.md`: safe to distil, unsafe for direct ingestion. It contains concise FAQ answers; Batch 012 only needs Windows backend, reset/rebuild, indexed-content inspection, irrelevant search, and dimension mismatch relationships.
- `docs/troubleshooting.md`: safe to distil, unsafe for direct ingestion. It contains recovery commands; Batch 012 only needs stats, force re-index, reset, source markdown, provider/model, API key, Windows, and Milvus Lite released relationships.

## Statement evidence

- Statement: Zero-config quick start uses local embeddings and Milvus Lite without an API key.
  Evidence: `docs/getting-started.md:27-60`.
- Statement: Milvus Lite is for personal use and development; Milvus Server is for self-hosted teams; Zilliz Cloud is for production and managed operations.
  Evidence: `docs/getting-started.md:349-487`; `docs/index.md:151-158`.
- Statement: Windows should use Milvus Server, Zilliz Cloud, or WSL2 instead of native Milvus Lite.
  Evidence: `docs/getting-started.md:371-374`; `docs/faq.md:3-13`; `docs/troubleshooting.md:33-44`.
- Statement: The agent loop is recall, think, remember.
  Evidence: `docs/getting-started.md:194-281`; `docs/python-api.md:188-272`.
- Statement: Remember writes to a daily markdown log and then re-indexes.
  Evidence: `docs/getting-started.md:211-274`; `docs/python-api.md:205-232`.
- Statement: Python API per-user isolation uses paths, collection, and milvus_uri.
  Evidence: `docs/python-api.md:339-377`.
- Statement: Directory plus collection isolation keeps users in separate markdown directories and collections so they never see each other's data.
  Evidence: `docs/python-api.md:342-356`.
- Statement: Separate Milvus Lite database files provide the strongest per-user isolation.
  Evidence: `docs/python-api.md:358-367`.
- Statement: Troubleshooting missing results starts with `memsearch stats`, then force re-index if count is zero or low.
  Evidence: `docs/troubleshooting.md:5-19`; `docs/faq.md:48-63`.
- Statement: Irrelevant or stale results should be handled by re-indexing, more specific queries, and checking embedding provider/model.
  Evidence: `docs/faq.md:67-83`; `docs/troubleshooting.md:5-19`.
- Statement: Dimension mismatch means the collection dimension differs from the current embedding provider/model, and reset/rebuild fixes it.
  Evidence: `docs/faq.md:85-96`; `docs/troubleshooting.md:21-31`.
- Statement: Reset drops the vector index but not source markdown.
  Evidence: `docs/faq.md:15-26`; `docs/troubleshooting.md:73-83`.
