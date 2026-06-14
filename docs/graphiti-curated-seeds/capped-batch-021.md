# Capped batch 021: platform index relationship boundaries

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils the four platform index pages that were not explicitly covered by earlier source reviews.
It does not ingest `.memsearch/memory` or raw task transcripts.

## Platform index relationships

Claude Code uses hooks for lifecycle events, skills for intelligent retrieval, and the memsearch CLI for tool access.
Claude Code does not require MCP servers, sidecar services, or extra network round-trips for the plugin.
Claude Code memory recall runs through a forked subagent context.
Claude Code stores memory as transparent Markdown files.
Claude Code compares against claude-mem by using forked subagent recall instead of MCP tools in the main context.

Codex uses shell hooks and a memory-recall skill.
Codex uses a Stop hook that calls `codex exec --ephemeral -s read-only -c features.hooks=false`.
Codex uses hook isolation so summarisation can reuse normal auth without recursively triggering hooks.
Codex handles missing `SessionEnd` with orphan cleanup.
Codex handles Milvus Lite by skipping concurrent index operations in Lite mode.

OpenClaw uses a TypeScript plugin with `kind: memory`.
OpenClaw replaces the built-in memory-core plugin with hybrid semantic search.
OpenClaw captures conversations after each turn through the `agent_end` hook.
OpenClaw injects cold-start context through the `before_agent_start` hook.
OpenClaw isolates memories by per-agent directory and per-agent Milvus collection.

OpenCode uses a TypeScript plugin.
OpenCode captures conversations through a background SQLite daemon.
OpenCode injects cold-start context through the `system.transform` hook.
OpenCode self-manages its daemon through a PID-file singleton, automatic restart, and persistent state.
OpenCode currently does not support native Windows for the plugin; it requires WSL2 or another POSIX-compatible shell on Windows.

## Cross-platform relationships

Claude Code, Codex, OpenClaw, and OpenCode all use Markdown memory as the portable source format.
Claude Code, Codex, OpenClaw, and OpenCode all use ONNX bge-m3 locally by default for embeddings.
Claude Code, Codex, OpenClaw, and OpenCode all support progressive recall.
Codex, OpenClaw, and OpenCode memories are intended to be searchable from the other memsearch-supported platforms.
OpenClaw and OpenCode both support cold-start context injection, but OpenClaw uses `before_agent_start` and OpenCode uses `system.transform`.
OpenClaw and OpenCode both use TypeScript plugins, but OpenClaw uses hooks while OpenCode uses a SQLite polling daemon.

