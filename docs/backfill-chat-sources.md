# Chat backfill sources

## Official export blocker

Official ChatGPT and Claude Chat export samples are not present yet.

Expected local placement:

```text
/Users/dominicmonkhouse/Projects/memsearch/.local/chat-exports/
```

Required samples before implementing official export parsers:

- ChatGPT export zip or extracted folder containing `conversations.json` or `chat.html`.
- Claude export zip or extracted folder containing official conversation JSON or HTML.

The backfill pipeline must not guess these export shapes. Export parsers stay blocked until real samples exist in `.local/chat-exports/`.

## Git safety

`.local/` is listed in `.gitignore`, so downloaded export archives placed under `.local/chat-exports/` will stay out of git.

## Current supported local sources

- Claude Code JSONL under `~/.claude/projects/`.
- Codex rollout JSONL under `~/.codex/sessions/`.
- Proven Claude Desktop/Cowork local-agent JSONL under `~/Library/Application Support/Claude/local-agent-mode-sessions/**/.claude/projects/**/*.jsonl`.

Current skipped sources:

- Claude Desktop audit logs.
- Claude Desktop subagent transcripts by default.
- Claude Desktop `claude-code-sessions` metadata, treated as possible Claude Code duplicates.
- ChatGPT, Claude, and Manus cache files until a proven conversation shape or official export is available.
