<!--
MON-316 capped Graphiti relationship seed batch 008 corrective reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-008-sources.md
-->

# Platform memory recall anchor corrections

Claude Code memory recall is separate from OpenClaw memory tools.
Claude Code memory recall does not use OpenClaw memory tools.
Claude Code memory recall execution context is forked subagent.
Codex memory recall execution context is main context.
OpenClaw memory tools registration API is `registerTool`.
OpenCode memory tools registration API is `tool() API`.
`registerTool` relates to OpenClaw memory tools.
`tool() API` relates to OpenCode memory tools.

# Manual trigger anchor corrections

`/memory-recall` is the Claude Code manual memory recall trigger.
`$memory-recall` is the Codex manual memory recall trigger.
`/memory-recall` is the OpenClaw manual memory recall trigger.
`/memory-recall` is the OpenCode manual memory recall trigger.
Claude Code, OpenClaw, and OpenCode share the `/memory-recall` manual trigger.
Codex differs by using the `$memory-recall` manual trigger.

# Transcript command anchor corrections

`parse-rollout.sh` is the Codex L3 rollout drill-down command.
Codex L3 uses `parse-rollout.sh`.
`parse-transcript.sh` is the OpenClaw memory_transcript JSONL parser.
OpenClaw memory_transcript uses `parse-transcript.sh`.
OpenClaw memory_transcript uses `transcript_path`.
OpenCode memory_transcript uses `session_id`.
OpenCode memory_transcript can use `turn_id`.
OpenCode memory_transcript reads SQLite.
