# Capped batch 015 correction relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti platform lifecycle tuning.

## Cold-start correction relationships

Platform cold-start injection answer includes Claude Code, SessionStart, Codex, memory file count and date range, OpenClaw, before_agent_start, OpenCode, and system.transform.
Claude Code cold-start injection is SessionStart additionalContext.
Codex cold-start injection includes memory file count and date range.
OpenClaw cold-start injection is before_agent_start prependContext.
OpenCode cold-start injection is system.transform system-prompt injection.

## Capture isolation correction relationships

Platform capture isolation answer includes Claude Code, `CLAUDECODE=`, Codex, `features.hooks=false`, OpenClaw, `MEMSEARCH_NO_WATCH`, OpenCode, and `XDG_CONFIG_HOME`.
Claude Code recursion prevention uses `CLAUDECODE=` and `MEMSEARCH_NO_WATCH=1`.
Codex recursion prevention uses `features.hooks=false` on child `codex exec`.
OpenCode recursion prevention uses isolated `XDG_CONFIG_HOME` without plugins.

## Watch and index correction relationships

Platform watch/index answer includes Claude Code, `memsearch watch`, Codex, Milvus Lite, one-time index, OpenClaw, background, OpenCode, and `capture-daemon.py`.
Codex Milvus Lite mode uses one-time index and skips continuous watch.
Codex Server mode can use `memsearch watch`.
OpenCode indexing is driven by `capture-daemon.py`.

## OpenCode sidecar correction relationships

OpenCode sidecar boundary answer includes OpenCode SQLite, source of truth, markdown, `opencode-turns.db`, derived capture state, and session+turn anchor.
OpenCode SQLite is the source of truth for original transcript reads.
OpenCode markdown memory files are the source of truth for MemSearch memory recall.
`opencode-turns.db` is not the source of truth.
`opencode-turns.db` is derived capture state only.
