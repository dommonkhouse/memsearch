# Batch 008 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti platform memory recall mechanics tuning.

## Source safety decisions

- `docs/platforms/claude-code/memory-recall.md`: safe to distil, unsafe for direct ingestion. It contains examples and comparison prose; Batch 008 only needs execution context, trigger, and transcript-source relationships.
- `docs/platforms/codex/memory-recall.md`: safe to distil, unsafe for direct ingestion. It contains examples and tips; Batch 008 only needs context, trigger, L2 fallback, and rollout-source relationships.
- `docs/platforms/openclaw/memory-tools.md`: safe to distil, unsafe for direct ingestion. It contains examples and comparison tables; Batch 008 only needs tool registration, trigger, and JSONL transcript relationships.
- `docs/platforms/opencode/memory-tools.md`: safe to distil, unsafe for direct ingestion. It contains examples and comparison tables; Batch 008 only needs tool registration, trigger, and SQLite transcript relationships.

## Statement evidence

- Statement: Claude Code memory recall runs in a forked subagent context and keeps intermediate results out of the main conversation.
  Evidence: `docs/platforms/claude-code/memory-recall.md:3`; `docs/platforms/claude-code/memory-recall.md:80`; `docs/platforms/claude-code/memory-recall.md:133-142`.
- Statement: Claude Code uses `/memory-recall` as the manual trigger and can auto-invoke recall.
  Evidence: `docs/platforms/claude-code/memory-recall.md:84-103`.
- Statement: Claude Code L3 transcript drill-down uses JSONL and `python3 transcript.py`.
  Evidence: `docs/platforms/claude-code/memory-recall.md:26-32`; `docs/platforms/claude-code/memory-recall.md:54-64`.
- Statement: Codex memory recall uses `$memory-recall`, runs in main context, and exposes intermediate results in the conversation.
  Evidence: `docs/platforms/codex/memory-recall.md:3-18`; `docs/platforms/codex/memory-recall.md:89-105`.
- Statement: Codex L2 can fall back to direct file read, and L3 uses `parse-rollout.sh` when a rollout path exists.
  Evidence: `docs/platforms/codex/memory-recall.md:39-55`; `docs/platforms/codex/memory-recall.md:80-83`.
- Statement: OpenClaw registers memory tools through `registerTool` and captures current agent context.
  Evidence: `docs/platforms/openclaw/memory-tools.md:1-4`.
- Statement: OpenClaw has `memory_search`, `memory_get`, and `memory_transcript`; `memory_transcript` accepts `transcript_path` and parses OpenClaw JSONL through `parse-transcript.sh`.
  Evidence: `docs/platforms/openclaw/memory-tools.md:7-13`; `docs/platforms/openclaw/memory-tools.md:52-58`.
- Statement: OpenClaw uses `/memory-recall` as the manual trigger and can auto-invoke memory tools.
  Evidence: `docs/platforms/openclaw/memory-tools.md:17-30`.
- Statement: OpenCode registers memory tools through the `tool()` API and exposes them to the LLM during conversation.
  Evidence: `docs/platforms/opencode/memory-tools.md:1-4`.
- Statement: OpenCode `memory_transcript` accepts `session_id`, optional `turn_id`, optional `context`, and optional `limit`; it reads OpenCode SQLite through `parse-transcript.py`.
  Evidence: `docs/platforms/opencode/memory-tools.md:7-13`; `docs/platforms/opencode/memory-tools.md:52-60`.
- Statement: OpenCode uses `/memory-recall` as the manual trigger and can auto-invoke memory tools.
  Evidence: `docs/platforms/opencode/memory-tools.md:17-30`.
- Statement: OpenCode can query memory non-interactively through `opencode run`.
  Evidence: `docs/platforms/opencode/memory-tools.md:93-105`.
- Statement: Claude Code memory recall is separate from OpenClaw memory tools.
  Evidence: `docs/platforms/claude-code/memory-recall.md:1-32`; `docs/platforms/openclaw/memory-tools.md:1-13`.
- Statement: `registerTool` is the OpenClaw memory tool registration pattern.
  Evidence: `docs/platforms/openclaw/memory-tools.md:1-4`.
- Statement: `tool()` API is the OpenCode memory tool registration pattern.
  Evidence: `docs/platforms/opencode/memory-tools.md:1-4`.
- Statement: `/memory-recall` is the manual memory recall trigger for Claude Code, OpenClaw, and OpenCode.
  Evidence: `docs/platforms/claude-code/memory-recall.md:84-90`; `docs/platforms/openclaw/memory-tools.md:17-23`; `docs/platforms/opencode/memory-tools.md:17-23`.
- Statement: `$memory-recall` is the manual memory recall trigger for Codex.
  Evidence: `docs/platforms/codex/memory-recall.md:7-16`.
- Statement: `parse-rollout.sh` is the Codex L3 rollout drill-down command.
  Evidence: `docs/platforms/codex/memory-recall.md:39-43`; `docs/platforms/codex/memory-recall.md:80-83`.
- Statement: `parse-transcript.sh` is the OpenClaw JSONL transcript parser.
  Evidence: `docs/platforms/openclaw/memory-tools.md:7-13`.
