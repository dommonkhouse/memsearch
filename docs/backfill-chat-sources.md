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
- ChatGPT and Claude cache files until official exports are available.
- Manus local app and browser files are probe-only. Current local files are Chromium cache and IndexedDB/LevelDB artefacts, not a proven transcript format.

## Manus route

Manus has a public API for creating and managing agent tasks, including multi-turn task messages, but this does not prove access to all existing product chat history. Manus also documents compliance/e-discovery export APIs, but those are activation-only and not general product access.

Until either an official user export, approved compliance export, or clean local transcript shape is available, Manus entries remain skipped with reasons such as `indexeddb_probe_only`, `cache_probe_only`, or `unknown_format`.

## Pilot run 2026-06-02

MacBook pilot:

- Output: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/20260602-131937/`
- Converted: 23
- Skipped: 64
- Errors: 0
- Converted products: Claude Code 10, Codex 10, Claude Desktop/Cowork 3

Mac Mini pilot:

- Output copied locally to: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/20260602-131937-mini/`
- Converted: 22
- Skipped: 60
- Errors: 0
- Converted products: Claude Code 10, Codex 10, Claude Desktop/Cowork 2

Secret scan:

- Filtered scan returned `hits 0` across both pilot runs.
- Redaction now removes `computer:///sessions/...` links and `*-service-account-key.json` filenames from rendered markdown.

Indexing blocker:

- Do not index pilot or production imported chats yet.
- `memsearch stats` currently reports an index, but searching `backfill-agent:codex` returns `claude-config` memory rather than `.memsearch/memory/historical-sessions`.
- Searching with `--source-prefix /Users/dominicmonkhouse/Projects/.memsearch/memory/historical-sessions` returns no results.
- Production indexing remains blocked until the target Memsearch collection is confirmed to contain existing historical-session chunks.
