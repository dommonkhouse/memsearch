# Capped batch 016 correction relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti troubleshooting and memory-tool tuning.

## Status/API-key correction relationships

Claude status API-key troubleshooting answer includes Claude Code, status line, API key, memory recording, `.md files`, semantic search and indexing, and ONNX.
Claude Code status line appears at session start.
Missing API key still allows memory recording to write `.md files`.
Missing API key disables semantic search and indexing.
ONNX requires no API key.

## Watch recovery correction relationships

Claude watch recovery answer includes `.memsearch/.watch.pid`, `memsearch watch`, orphaned processes, Milvus Lite, one-time indexing, Milvus Server, and Zilliz Cloud.
`.memsearch/.watch.pid` is the watcher PID file.
Milvus Lite falls back to one-time indexing.
Milvus Server and Zilliz Cloud support real-time indexing.

## Codex recall fallback correction relationships

Codex recall fallback answer includes Codex, main context, `memsearch expand`, direct file read, source, start_line, end_line, and `parse-rollout.sh`.
Codex `$memory-recall` runs in the main context.
Codex direct file read fallback uses source, start_line, and end_line.
Codex L3 drill-down uses `parse-rollout.sh` when rollout anchors exist.

## Memory-tool comparison correction relationships

Memory-tool comparison answer includes OpenClaw, OpenCode, three tools, memory_search, memory_get, memory_transcript, Milvus hybrid, and dense-only.
OpenClaw MemSearch has three tools.
OpenCode MemSearch has three tools.
MemSearch uses Milvus hybrid search.
memory-core, memory-lancedb, and opencode-mem are dense-only comparison targets.
