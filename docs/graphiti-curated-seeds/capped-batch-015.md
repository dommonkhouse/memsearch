# Capped batch 015: platform lifecycle relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils only platform lifecycle relationships from the four platform
how-it-works documents. It does not ingest `.memsearch/memory`.

## Platform cold-start injection relationships

Claude Code cold-start injection runs in the SessionStart hook.
Claude Code SessionStart reads recent memory files and injects recent memories as additionalContext.
Codex cold-start injection runs in the SessionStart hook.
Codex SessionStart injects memory file count and date range plus a hint to use `$memory-recall`.
OpenClaw cold-start injection runs in the before_agent_start hook.
OpenClaw before_agent_start returns prependContext from recent daily memory files.
OpenCode cold-start injection runs through the system.transform hook.
OpenCode system.transform pushes recent memories into the system prompt.

## Platform capture isolation relationships

Claude Code capture summarisation runs from the Stop hook.
Claude Code prevents recursive capture with stop_hook_active, `CLAUDECODE=`, and `MEMSEARCH_NO_WATCH=1`.
Codex capture summarisation runs from the Stop hook through `codex exec`.
Codex prevents recursive capture by running child `codex exec` with `features.hooks=false`.
OpenClaw capture summarisation runs from the agent_end event through `openclaw agent --local`.
OpenClaw uses `MEMSEARCH_NO_WATCH` during capture summarisation.
OpenCode capture summarisation runs inside `capture-daemon.py` through `opencode run`.
OpenCode prevents recursive capture by using isolated `XDG_CONFIG_HOME` and `XDG_DATA_HOME` without plugins.

## Platform watch and index mode relationships

Claude Code SessionStart starts `memsearch watch` and SessionEnd stops the watcher.
Codex has no SessionEnd hook.
Codex SessionStart starts `memsearch watch` in Milvus Server mode.
Codex SessionStart uses one-time index in Milvus Lite mode because Lite has a file lock.
OpenClaw writes memory on agent_end and triggers `memsearch index` in the background.
OpenCode uses `capture-daemon.py` to poll SQLite, write markdown, and trigger `memsearch index`.

## OpenCode sidecar boundary relationships

OpenCode SQLite is the source of truth for original transcript reads.
OpenCode markdown memory files are the source of truth for MemSearch memory recall.
`.memsearch/opencode-turns.db` is derived capture state only.
If markdown append succeeds but sidecar write fails, OpenCode replay uses the existing session+turn anchor to avoid duplicate memory entries.
