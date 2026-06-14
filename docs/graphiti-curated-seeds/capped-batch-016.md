# Capped batch 016: troubleshooting and memory-tool relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils only troubleshooting and memory-tool fallback relationships.
It does not ingest `.memsearch/memory`.

## Claude Code status and API-key troubleshooting relationships

Claude Code MemSearch shows a status line at session start.
The Claude Code status line includes embedding provider, Milvus URI, collection, API-key errors, and update notices.
If a required API key is missing, Claude Code memory recording still writes `.md` files.
If a required API key is missing, semantic search and indexing are disabled.
The default ONNX embedding provider needs no API key.
Fixing API-key errors means exporting the required key or switching to ONNX.

## Claude Code watch recovery and Milvus Lite boundary relationships

Claude Code MemSearch uses `.memsearch/.watch.pid` for the `memsearch watch` singleton.
Watch recovery checks `.memsearch/.watch.pid` and uses `kill -0` to verify whether the watcher is running.
Manual watch restart removes the stale PID file and starts `memsearch watch .memsearch/memory/`.
Troubleshooting orphaned watch processes uses `pgrep -f "memsearch watch"`.
Milvus Lite does not support concurrent access.
With Milvus Lite, plugins fall back to one-time indexing at session start.
For real-time indexing, use Milvus Server or Zilliz Cloud.

## Codex memory recall expand fallback relationships

Codex `$memory-recall` runs in the main context.
Codex L1 recall starts with `memsearch search`.
Codex L2 recall first tries `memsearch expand`.
If `memsearch expand` fails under sandbox restrictions, Codex reads the source file directly.
Codex direct file read fallback uses the search result `source`, `start_line`, and `end_line`.
Codex L3 drill-down uses `parse-rollout.sh` when a rollout anchor exists.

## OpenClaw and OpenCode memory-tool comparison relationships

OpenClaw MemSearch registers three memory tools: `memory_search`, `memory_get`, and `memory_transcript`.
OpenCode MemSearch registers three memory tools: `memory_search`, `memory_get`, and `memory_transcript`.
OpenClaw memory tools use Milvus hybrid search with dense, BM25, and RRF.
OpenCode memory tools use Milvus hybrid search with dense, BM25, and RRF.
OpenClaw memory-core is dense-only and search-only compared with MemSearch three-layer recall.
OpenClaw memory-lancedb uses LanceDB dense-only search compared with MemSearch Milvus hybrid search.
OpenCode opencode-mem is dense-only compared with MemSearch hybrid search.
