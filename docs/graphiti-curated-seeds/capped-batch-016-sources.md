# Capped batch 016 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti troubleshooting and memory-tool tuning.

## Reviewed source files

- `docs/platforms/claude-code/troubleshooting.md`: safe to distil, unsafe for direct ingestion. It contains status-line diagnostics, API-key behaviour, watch PID recovery, Milvus Lite indexing boundaries, and warm-up guidance.
- `docs/platforms/codex/memory-recall.md`: safe to distil, unsafe for direct ingestion. It contains Codex memory-recall execution context, L2 direct file fallback, and L3 rollout drill-down behaviour.
- `docs/platforms/openclaw/memory-tools.md`: safe to distil, unsafe for direct ingestion. It contains OpenClaw memory tool semantics and comparisons with memory-core and memory-lancedb.
- `docs/platforms/opencode/memory-tools.md`: safe to distil, unsafe for direct ingestion. It contains OpenCode memory tool semantics, sidecar boundary detail, and comparison with opencode-mem.

## Evidence statements

- Statement: Claude Code shows MemSearch status at session start with embedding provider, Milvus URI, collection, errors, and update notices.
  Evidence: `docs/platforms/claude-code/troubleshooting.md:7-20`.
- Statement: Missing API keys still allow memory recording to markdown, but disable semantic search and indexing.
  Evidence: `docs/platforms/claude-code/troubleshooting.md:22-39`.
- Statement: ONNX is the default local provider and requires no API key.
  Evidence: `docs/platforms/claude-code/troubleshooting.md:28-39`.
- Statement: Watch recovery uses `.memsearch/.watch.pid`, `kill -0`, manual restart, and orphan process checks.
  Evidence: `docs/platforms/claude-code/troubleshooting.md:72-94`.
- Statement: Milvus Lite falls back to one-time indexing, while Milvus Server or Zilliz Cloud support real-time indexing.
  Evidence: `docs/platforms/claude-code/troubleshooting.md:96-98`.
- Statement: Codex memory recall runs in main context and uses L1 search, L2 expand/direct file read, and L3 parse-rollout.
  Evidence: `docs/platforms/codex/memory-recall.md:16-35`; `docs/platforms/codex/memory-recall.md:37-47`; `docs/platforms/codex/memory-recall.md:91-103`.
- Statement: Codex direct file fallback uses source, start_line, and end_line when `memsearch expand` fails.
  Evidence: `docs/platforms/codex/memory-recall.md:37-47`.
- Statement: OpenClaw registers memory_search, memory_get, and memory_transcript through registerTool.
  Evidence: `docs/platforms/openclaw/memory-tools.md:1-11`.
- Statement: OpenClaw MemSearch is three-layer, Milvus hybrid, and richer than memory-core search-only dense recall.
  Evidence: `docs/platforms/openclaw/memory-tools.md:89-104`.
- Statement: OpenClaw MemSearch uses Milvus hybrid, while memory-lancedb uses LanceDB dense-only search.
  Evidence: `docs/platforms/openclaw/memory-tools.md:108-121`.
- Statement: OpenCode registers memory_search, memory_get, and memory_transcript through the tool API.
  Evidence: `docs/platforms/opencode/memory-tools.md:1-12`.
- Statement: OpenCode memory_transcript reads SQLite directly and does not require the sidecar DB.
  Evidence: `docs/platforms/opencode/memory-tools.md:9-12`; `docs/platforms/opencode/memory-tools.md:46-50`.
- Statement: OpenCode MemSearch uses Milvus hybrid search while opencode-mem is dense-only.
  Evidence: `docs/platforms/opencode/memory-tools.md:96-111`.
