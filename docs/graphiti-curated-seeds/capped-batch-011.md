<!--
MON-316 capped Graphiti relationship seed batch 011.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-011-sources.md
-->

# Plugin summarization routing relationships

memsearch plugin summarization routing is plugin-specific.
Each plugin keeps its current native summarizer when `plugins.<platform>.summarize.provider` is empty or `native`.
Plugin summarization settings do not fall back to `llm.model`.
To route plugin summarization through a memsearch-managed provider, define `llm.providers.<name>`.
After defining `llm.providers.<name>`, set `plugins.<platform>.summarize.provider` to that provider name.
`plugins.<platform>.summarize.model` overrides one plugin's native model.
Automatic capture can be disabled per project with `plugins.<platform>.summarize.enabled false --project`.

# Platform comparison relationships

Claude Code uses shell hooks for capture and SKILL.md for recall.
Claude Code uses Claude Code JSONL for L3 transcript format.
Claude Code installs through the plugin marketplace.
OpenClaw uses TypeScript registerTool and an agent_end hook.
OpenClaw uses memory_search tools for recall and OpenClaw JSONL for L3 transcript format.
OpenClaw installs with `openclaw plugins install --force` and hook permissions.
OpenCode uses an npm plugin and a SQLite daemon for capture.
OpenCode uses memory_search tools for recall and OpenCode SQLite for L3 transcript format.
Codex CLI uses shell hooks for capture and SKILL.md for recall.
Codex CLI uses rollout JSONL for L3 transcript format.
Codex CLI installs with `install.sh`.

# Agent framework integration relationships

memsearch integrates with LangChain by wrapping MemSearch in a LangChain BaseRetriever.
The LangChain BaseRetriever returns Documents with source, heading, and score metadata.
memsearch integrates with LangGraph by wrapping search_memory as a tool.
The LangGraph ReAct agent calls search_memory when it needs memory.
memsearch integrates with LlamaIndex by implementing a BaseRetriever that returns NodeWithScore objects.
memsearch integrates with CrewAI by registering search_memory as a CrewAI tool.
CrewAI agents can call search_memory before answering knowledge-base questions.

# Cross-platform sharing and isolation relationships

All memsearch plugins write standard markdown memory files.
All memsearch plugins derive collection names from the project directory using the same algorithm.
The same project directory maps to the same collection name.
Memories from the same project directory are shared memories across Claude Code, Codex CLI, OpenClaw, and OpenCode.
Different project directories are isolated by different collection names.
Shared memories require no manual configuration when platforms use the same project directory.
