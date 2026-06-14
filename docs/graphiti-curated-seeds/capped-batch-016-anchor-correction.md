# Capped batch 016 anchor correction relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti troubleshooting and memory-tool tuning.

## Status/API-key anchor relationships

status line is the Claude Code API-key troubleshooting anchor.
API key is the Claude Code missing-key troubleshooting anchor.
memory recording is the behaviour that still works when API key is missing.
semantic search and indexing are the behaviours disabled when API key is missing.
ONNX is the no-API-key embedding provider anchor.

## Watch recovery anchor relationships

`.memsearch/.watch.pid` is the watcher PID anchor.
`memsearch watch` is the watch recovery command anchor.
orphaned processes are found with the watch troubleshooting flow.
Milvus Lite is the one-time indexing boundary anchor.
Milvus Server and Zilliz Cloud are the real-time indexing anchors.

## Codex recall fallback anchor relationships

main context is the Codex recall execution anchor.
`memsearch expand` is the Codex L2 first path.
direct file read is the Codex L2 fallback path.
source, start_line, and end_line are the direct file read fallback anchors.
`parse-rollout.sh` is the Codex L3 rollout anchor.

## Memory-tool comparison anchor relationships

OpenClaw and OpenCode both expose three memory tools.
memory_search, memory_get, and memory_transcript are the three memory-tool anchors.
Milvus hybrid is the MemSearch search-quality anchor.
dense-only is the comparison weakness anchor for memory-core, memory-lancedb, and opencode-mem.
