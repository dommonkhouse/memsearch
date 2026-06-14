# Capped batch 021 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti platform-index tuning.

## Reviewed source files

- `docs/platforms/claude-code/index.md`: safe to distil, unsafe for direct ingestion. It contains broad product copy, diagrams, and comparison tables; Batch 021 only needs platform-specific capture, recall, storage, and comparison relationships.
- `docs/platforms/codex/index.md`: safe to distil, unsafe for direct ingestion. It contains platform positioning plus operational hook details; Batch 021 only needs shell-hook, Stop-hook, orphan-cleanup, and Milvus Lite relationships.
- `docs/platforms/openclaw/index.md`: safe to distil, unsafe for direct ingestion. It contains plugin positioning and install links; Batch 021 only needs memory-core replacement, per-agent isolation, hook, and cold-start relationships.
- `docs/platforms/opencode/index.md`: safe to distil, unsafe for direct ingestion. It contains comparison and platform-note detail; Batch 021 only needs SQLite-daemon, cold-start, daemon-management, and Windows-boundary relationships.

## Evidence statements

- Statement: Claude Code uses hooks, skills, and the CLI, with no MCP servers, sidecar services, or extra network round-trips.
  Evidence: `docs/platforms/claude-code/index.md:3-5`.
- Statement: Claude Code recall uses a forked subagent, hybrid search, transparent Markdown storage, ONNX by default, and no MCP overhead.
  Evidence: `docs/platforms/claude-code/index.md:58-78`.
- Statement: Claude Code differs from claude-mem by using forked subagent recall rather than MCP tools in the main context.
  Evidence: `docs/platforms/claude-code/index.md:91-115`.
- Statement: Codex has no native memory plugin ecosystem and memsearch fills that gap with shell hooks, memory-recall skill, cross-platform portability, and ONNX embedding by default.
  Evidence: `docs/platforms/codex/index.md:7-17`.
- Statement: Codex uses a Stop hook with `codex exec --ephemeral -s read-only -c features.hooks=false`.
  Evidence: `docs/platforms/codex/index.md:20-27`.
- Statement: Codex supports native capture, rollout drill-down, orphan cleanup, Milvus Lite lock handling, and local summarisation fallback.
  Evidence: `docs/platforms/codex/index.md:31-39`.
- Statement: OpenClaw uses a TypeScript plugin with `kind: memory` and replaces built-in memory-core with hybrid semantic search.
  Evidence: `docs/platforms/openclaw/index.md:1-31`.
- Statement: OpenClaw isolates by per-agent directory and per-agent Milvus collection, while sharing when agents point to the same project directory.
  Evidence: `docs/platforms/openclaw/index.md:35-53`.
- Statement: OpenClaw captures through `agent_end` and injects cold-start context through `before_agent_start`.
  Evidence: `docs/platforms/openclaw/index.md:57-73`.
- Statement: OpenCode uses a TypeScript plugin and captures via a background SQLite daemon.
  Evidence: `docs/platforms/opencode/index.md:1-3`; `docs/platforms/opencode/index.md:27-34`.
- Statement: OpenCode provides cross-platform memory through shared Markdown format and the same Milvus backend.
  Evidence: `docs/platforms/opencode/index.md:21-24`.
- Statement: OpenCode injects cold-start context through `system.transform` and self-manages its daemon with a PID singleton, automatic restart, and persistent state.
  Evidence: `docs/platforms/opencode/index.md:27-34`.
- Statement: OpenCode native Windows is not supported yet; the plugin needs WSL2 or another POSIX-compatible shell on Windows.
  Evidence: `docs/platforms/opencode/index.md:47-50`.

