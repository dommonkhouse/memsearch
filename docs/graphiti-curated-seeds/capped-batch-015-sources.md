# Capped batch 015 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti platform lifecycle tuning.

## Reviewed source files

- `docs/platforms/claude-code/how-it-works.md`: safe to distil, unsafe for direct ingestion. It contains platform lifecycle implementation details, hook flow, and capture recursion guards.
- `docs/platforms/codex/how-it-works.md`: safe to distil, unsafe for direct ingestion. It contains Codex hook lifecycle details, Milvus Lite lock handling, and `codex exec` recursion prevention.
- `docs/platforms/openclaw/how-it-works.md`: safe to distil, unsafe for direct ingestion. It contains OpenClaw event hook details, tool registration, agent_end capture, and before_agent_start context injection.
- `docs/platforms/opencode/how-it-works.md`: safe to distil, unsafe for direct ingestion. It contains daemon capture, SQLite transcript source, XDG isolation, and sidecar state boundaries.

## Evidence statements

- Statement: Claude Code cold-start injection runs in SessionStart and returns recent memories as additionalContext.
  Evidence: `docs/platforms/claude-code/how-it-works.md:44-53`; `docs/platforms/claude-code/how-it-works.md:56-65`.
- Statement: Codex cold-start injection runs in SessionStart and injects memory file count, date range, and `$memory-recall` hint.
  Evidence: `docs/platforms/codex/how-it-works.md:13-22`; `docs/platforms/codex/how-it-works.md:49-58`.
- Statement: OpenClaw cold-start injection uses before_agent_start and returns prependContext from recent daily memories.
  Evidence: `docs/platforms/openclaw/how-it-works.md:5-10`; `docs/platforms/openclaw/how-it-works.md:106-122`.
- Statement: OpenCode cold-start injection uses system.transform and pushes recent memories into the system prompt.
  Evidence: `docs/platforms/opencode/how-it-works.md:5-10`; `docs/platforms/opencode/how-it-works.md:118-135`.
- Statement: Claude Code prevents recursive capture with stop_hook_active, `CLAUDECODE=`, and `MEMSEARCH_NO_WATCH=1`.
  Evidence: `docs/platforms/claude-code/how-it-works.md:90-101`; `docs/platforms/claude-code/how-it-works.md:242-251`.
- Statement: Codex prevents recursive capture by disabling hooks in child `codex exec`.
  Evidence: `docs/platforms/codex/how-it-works.md:90-109`; `docs/platforms/codex/how-it-works.md:251-259`.
- Statement: OpenClaw captures from agent_end and summarises with `openclaw agent --local`.
  Evidence: `docs/platforms/openclaw/how-it-works.md:46-80`; `docs/platforms/openclaw/how-it-works.md:97-104`.
- Statement: OpenCode prevents recursive capture with isolated XDG config/data homes and no plugins directory.
  Evidence: `docs/platforms/opencode/how-it-works.md:78-101`.
- Statement: Claude Code starts watch at SessionStart and stops watch at SessionEnd.
  Evidence: `docs/platforms/claude-code/how-it-works.md:44-53`; `docs/platforms/claude-code/how-it-works.md:153-156`.
- Statement: Codex starts watch only in Server mode and uses one-time index in Milvus Lite mode.
  Evidence: `docs/platforms/codex/how-it-works.md:49-73`.
- Statement: OpenClaw triggers background non-blocking indexing after capture.
  Evidence: `docs/platforms/openclaw/how-it-works.md:19-35`; `docs/platforms/openclaw/how-it-works.md:68-80`.
- Statement: OpenCode daemon polls SQLite, writes markdown, persists sidecar state, and re-indexes.
  Evidence: `docs/platforms/opencode/how-it-works.md:27-76`.
- Statement: OpenCode SQLite is the source of truth for transcript reads and opencode-turns.db is derived capture state.
  Evidence: `docs/platforms/opencode/how-it-works.md:65-76`; `docs/platforms/opencode/how-it-works.md:140-151`.
