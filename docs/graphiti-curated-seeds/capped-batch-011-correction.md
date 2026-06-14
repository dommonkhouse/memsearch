<!--
MON-316 capped Graphiti relationship seed batch 011 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-011-sources.md
-->

# Plugin summarization routing correction relationships

Plugin summarization routing answer includes plugin-specific, native, llm.providers, summarize.provider, llm.model, and do not fall back.
Plugin summarization routing is plugin-specific.
Plugin summarization uses native when summarize.provider is empty or native.
Plugin summarization can use llm.providers by setting summarize.provider to a named provider.
Plugin summarization settings do not fall back to llm.model.

# Platform comparison matrix correction relationships

Platform comparison matrix answer includes Claude Code, OpenClaw, OpenCode, Codex CLI, Shell hooks, SQLite daemon, SKILL.md, and rollout JSONL.
Claude Code uses Shell hooks and SKILL.md.
OpenClaw uses TypeScript registerTool and OpenClaw JSONL.
OpenCode uses an npm plugin, SQLite daemon, and OpenCode SQLite.
Codex CLI uses Shell hooks, SKILL.md, and rollout JSONL.

# Agent framework integrations correction relationships

Agent framework integrations answer includes LangChain, BaseRetriever, LangGraph, ReAct agent, LlamaIndex, NodeWithScore, CrewAI, and tool.
LangChain integrates through a BaseRetriever.
LangGraph integrates through a search_memory tool used by a ReAct agent.
LlamaIndex integrates through a BaseRetriever that returns NodeWithScore.
CrewAI integrates through a search_memory tool.

# Cross-platform sharing isolation correction relationships

Cross-platform sharing and isolation answer includes same project directory, same collection name, different project directories, standard markdown, shared memories, and isolated.
All plugins write standard markdown.
The same project directory maps to the same collection name.
The same collection name creates shared memories across platforms.
Different project directories are isolated by different collection names.
