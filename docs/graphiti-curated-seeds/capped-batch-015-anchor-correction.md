# Capped batch 015 anchor correction relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti platform lifecycle tuning.

## Cold-start anchor relationships

SessionStart is the Claude Code cold-start injection anchor.
SessionStart is the Codex cold-start injection anchor.
before_agent_start is the OpenClaw cold-start injection anchor.
system.transform is the OpenCode cold-start injection anchor.
memory file count and date range is a Codex cold-start detail.

## Capture isolation anchor relationships

`CLAUDECODE=` is a Claude Code capture-isolation anchor.
`features.hooks=false` is a Codex capture-isolation anchor.
`MEMSEARCH_NO_WATCH` is a platform capture-isolation anchor.
`XDG_CONFIG_HOME` is an OpenCode capture-isolation anchor.

## Watch/index anchor relationships

`memsearch watch` is a Claude Code and Codex Server-mode watcher anchor.
Milvus Lite is a Codex one-time index anchor.
one-time index is the Codex Milvus Lite behaviour.
background index is the OpenClaw capture behaviour.
`capture-daemon.py` is the OpenCode capture and indexing anchor.

## Sidecar boundary anchor relationships

OpenCode SQLite is the transcript source-of-truth anchor.
markdown is the MemSearch memory source-of-truth anchor.
`opencode-turns.db` is the derived capture state anchor.
session+turn anchor is the OpenCode duplicate-prevention anchor.
