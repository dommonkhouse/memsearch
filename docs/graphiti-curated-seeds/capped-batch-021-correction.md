# Capped batch 021 correction: platform index anchors

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

Claude Code platform memory uses hooks, skills, and the memsearch CLI.
Claude Code platform memory does not require MCP servers.
Claude Code platform recall uses forked subagent recall.

Codex platform memory uses shell hooks and a memory-recall skill.
Codex Stop hook uses `codex exec --ephemeral -s read-only -c features.hooks=false`.
Codex Stop hook isolation prevents recursive hook triggering.
Codex Milvus Lite handling skips concurrent index operations in Lite mode.

OpenClaw platform memory uses a TypeScript plugin with `kind: memory`.
OpenClaw platform memory replaces memory-core.
OpenClaw capture uses `agent_end`.
OpenClaw cold-start context uses `before_agent_start`.
OpenClaw memory isolation uses per-agent directories and per-agent Milvus collections.

OpenCode platform memory uses a TypeScript plugin.
OpenCode capture uses a background SQLite daemon.
OpenCode cold-start context uses `system.transform`.
OpenCode daemon management uses a PID-file singleton and automatic restart.
OpenCode native Windows is not supported yet for the plugin.

