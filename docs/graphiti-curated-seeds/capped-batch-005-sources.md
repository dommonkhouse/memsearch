# Batch 005 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti installation, recovery, and troubleshooting recall tuning.

## Source safety decisions

- `docs/home/configuration.md`: safe to distil, unsafe for direct ingestion. It includes user-facing examples, hosted-service signup links, and broader configuration reference details that would be noisy as raw graph facts.
- `docs/troubleshooting.md`: safe to distil, unsafe for direct ingestion. It includes recovery commands and reset examples that should appear only as contextual graph facts, not blanket instructions.
- `docs/platforms/codex/how-it-works.md`: safe to distil, unsafe for direct ingestion. It includes Codex hook implementation detail and examples beyond the focused Milvus Lite/Server relationship.
- `docs/platforms/claude-code/memory-recall.md`: safe to distil, unsafe for direct ingestion. It includes long examples and comparative marketing content; Batch 005 only needs the progressive disclosure relationship map.

## Statement evidence

- Statement: MemSearch local embedding profile uses ONNX by default and needs no API key.
  Evidence: `docs/home/configuration.md:24-32`; `docs/platforms/codex/how-it-works.md:58-66`.
- Statement: OpenAI-compatible embedding providers need provider API keys, including `OPENAI_API_KEY`, `GOOGLE_API_KEY`, and `VOYAGE_API_KEY`.
  Evidence: `docs/home/configuration.md:24-36`; `docs/troubleshooting.md:39-49`.
- Statement: Milvus Lite is the default local backend, zero config, and single file.
  Evidence: `docs/home/configuration.md:42-50`; `docs/platforms/codex/how-it-works.md:76-85`.
- Statement: Zilliz Cloud is the recommended managed backend and supports concurrent access and real-time indexing.
  Evidence: `docs/home/configuration.md:51-62`; `docs/platforms/codex/how-it-works.md:76-85`.
- Statement: Milvus Server is the self-hosted Docker backend for advanced users.
  Evidence: `docs/home/configuration.md:63-68`; `docs/troubleshooting.md:52-62`.
- Statement: Windows should use Milvus Server, Zilliz Cloud, or WSL2 instead of native Milvus Lite.
  Evidence: `docs/troubleshooting.md:52-62`.
- Statement: Dimension mismatch means the current embedding provider/model produces a different vector size from the existing Milvus collection.
  Evidence: `docs/troubleshooting.md:27-37`.
- Statement: Dimension mismatch recovery resets the vector index and re-indexes Markdown files.
  Evidence: `docs/troubleshooting.md:27-37`; `docs/troubleshooting.md:83-97`.
- Statement: Changing embedding provider/model requires re-indexing.
  Evidence: `docs/home/configuration.md:34-39`; `docs/troubleshooting.md:21-25`; `docs/troubleshooting.md:83-97`.
- Statement: Markdown is the source of truth during reset and rebuild, while Milvus is a rebuildable derived index.
  Evidence: `docs/troubleshooting.md:27-37`; `docs/troubleshooting.md:83-97`.
- Statement: Missing search results should start with `memsearch stats` and inspect actual results with `memsearch search`.
  Evidence: `docs/troubleshooting.md:5-25`; `docs/troubleshooting.md:98-111`.
- Statement: If stats are zero or unexpectedly low, rebuild the index.
  Evidence: `docs/troubleshooting.md:5-25`.
- Statement: Search results can be stale when the index needs re-indexing.
  Evidence: `docs/troubleshooting.md:5-25`; `docs/troubleshooting.md:83-97`.
- Statement: Search results can be weak when a query is too short or vague.
  Evidence: `docs/troubleshooting.md:17-25`.
- Statement: Search results can be wrong when the embedding provider/model changed after collection creation.
  Evidence: `docs/troubleshooting.md:17-25`; `docs/troubleshooting.md:83-97`.
- Statement: Remote Milvus stats may lag after upserts and search results are the better source of truth.
  Evidence: `docs/troubleshooting.md:113-117`.
- Statement: Progressive disclosure starts with L1 search, continues with L2 expand, and can continue with L3 transcript.
  Evidence: `docs/platforms/claude-code/memory-recall.md:9-34`.
- Statement: L1 search uses `memsearch search`, L2 expand uses `memsearch expand`, and L3 transcript uses transcript commands or plugin transcript parsers.
  Evidence: `docs/platforms/claude-code/memory-recall.md:20-34`; `docs/platforms/codex/how-it-works.md:247-261`.
- Statement: L2 expand returns the full markdown section around a chunk.
  Evidence: `docs/platforms/claude-code/memory-recall.md:20-34`; `docs/platforms/claude-code/memory-recall.md:38-74`.
- Statement: L3 transcript returns original conversation turns.
  Evidence: `docs/platforms/claude-code/memory-recall.md:20-34`; `docs/platforms/codex/how-it-works.md:247-261`.
- Statement: Codex Server mode starts `memsearch watch`.
  Evidence: `docs/platforms/codex/how-it-works.md:58-74`.
- Statement: Codex Milvus Lite mode runs a one-time index and skips `memsearch watch` because Milvus Lite uses a file-level lock.
  Evidence: `docs/platforms/codex/how-it-works.md:58-85`.
- Statement: For real-time indexing without Milvus Lite lock issues, use Milvus Server or Zilliz Cloud.
  Evidence: `docs/platforms/codex/how-it-works.md:76-85`.
- Statement: ONNX is the default local embedding profile for MemSearch and requires no API key.
  Evidence: `docs/home/configuration.md:24-32`; `docs/platforms/codex/how-it-works.md:58-66`.
- Statement: Milvus Lite does not provide Windows binaries.
  Evidence: `docs/troubleshooting.md:52-62`.
- Statement: Windows should not use native Milvus Lite for MemSearch.
  Evidence: `docs/troubleshooting.md:52-62`.
- Statement: Windows alternatives are Milvus Server via Docker, Zilliz Cloud, and WSL2.
  Evidence: `docs/troubleshooting.md:52-62`.
- Statement: Dimension mismatch recovery runs `memsearch reset --yes` and `memsearch index`.
  Evidence: `docs/troubleshooting.md:27-37`; `docs/troubleshooting.md:83-97`.
- Statement: Dimension mismatch recovery resets only the vector index and keeps Markdown as the source of truth.
  Evidence: `docs/troubleshooting.md:27-37`.
- Statement: Changing the embedding provider/model requires `memsearch index --force`.
  Evidence: `docs/home/configuration.md:34-39`.
- Statement: Missing search results first step is `memsearch stats` and second step is `memsearch search`.
  Evidence: `docs/troubleshooting.md:5-15`; `docs/troubleshooting.md:98-111`.
- Statement: If `memsearch stats` shows zero or unexpectedly low count, rebuild the index.
  Evidence: `docs/troubleshooting.md:5-25`.
- Statement: Queries that are too short or vague can return weak search results.
  Evidence: `docs/troubleshooting.md:17-25`.
- Statement: Stale index state can cause missing search results.
  Evidence: `docs/troubleshooting.md:17-25`.
