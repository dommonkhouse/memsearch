<!--
MON-316 capped Graphiti relationship seed batch 008 transcript-source anchor.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-008-sources.md
-->

# Cross-platform memory transcript source anchor

Memory transcript sources differ across Claude Code, Codex, OpenClaw, and OpenCode.
Claude Code memory transcript source is JSONL.
Codex memory transcript source is `parse-rollout.sh`.
Codex memory transcript drill-down uses `parse-rollout.sh`.
OpenClaw memory transcript source is OpenClaw JSONL through `parse-transcript.sh`.
OpenCode memory transcript source is OpenCode SQLite.
OpenCode memory transcript reads SQLite with `session_id` and optional `turn_id`.
