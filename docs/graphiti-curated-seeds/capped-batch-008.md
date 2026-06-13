<!--
MON-316 capped Graphiti relationship seed batch 008.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-008-sources.md
-->

# Platform memory recall execution contexts

Claude Code memory recall runs in a forked subagent context.
Claude Code forked subagent context keeps intermediate memory search results out of the main conversation.
Codex memory recall runs in the main conversation context.
Codex main context means search and expand results are visible in the conversation.
OpenClaw memory tools register through the `registerTool` factory pattern.
OpenClaw memory tools capture the current agent context when invoked.
OpenCode memory tools register through the `tool()` API.
OpenCode memory tools are available to the LLM during conversation.

# Platform manual memory recall triggers

Claude Code manual memory recall trigger is `/memory-recall`.
Codex manual memory recall trigger is `$memory-recall`.
OpenClaw manual memory recall trigger is `/memory-recall`.
OpenCode manual memory recall trigger is `/memory-recall`.
Claude Code, Codex, OpenClaw, and OpenCode can all invoke memory recall automatically when past context would help.

# Platform transcript source relationships

Claude Code L3 transcript drill-down reads original conversation turns from JSONL.
Claude Code L3 transcript command uses `python3 transcript.py`.
Codex L3 rollout drill-down uses `parse-rollout.sh`.
Codex rollout drill-down depends on a rollout path being present.
OpenClaw `memory_transcript` accepts a `transcript_path`.
OpenClaw `memory_transcript` parses original OpenClaw JSONL through `parse-transcript.sh`.
OpenCode `memory_transcript` accepts `session_id`, optional `turn_id`, optional `context`, and optional `limit`.
OpenCode `memory_transcript` reads original conversation from OpenCode SQLite through `parse-transcript.py`.
OpenCode `memory_transcript` does not require the sidecar DB for transcript reads.

# OpenClaw and OpenCode transcript differences

OpenClaw `memory_transcript` uses `transcript_path`.
OpenClaw `memory_transcript` reads JSONL transcripts.
OpenCode `memory_transcript` uses `session_id`.
OpenCode `memory_transcript` can use `turn_id`.
OpenCode `memory_transcript` reads SQLite conversations.
OpenCode `.memsearch/opencode-turns.db` stores derived capture checkpoints and stable turn ordering for the daemon.
