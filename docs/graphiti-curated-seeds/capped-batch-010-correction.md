<!--
MON-316 capped Graphiti relationship seed batch 010 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-010-sources.md
-->

# Product positioning retrieval correction relationships

When asked when to choose memsearch instead of Claude Code native memory, mem0, Letta, or qmd, answer with alternatives-fit.
The alternatives-fit answer includes memsearch, Claude Code native, mem0, Letta, qmd, coding CLI, and local markdown search engine.
memsearch fits coding CLI memory across Claude Code, OpenClaw, OpenCode, and Codex CLI.
Claude Code native fits tiny or project-instruction-like memory.
mem0 fits generic LLM applications.
Letta fits full agent runtime or MemFS needs.
qmd fits a local markdown search engine.

When asked why memsearch treats Markdown as source of truth and Milvus as a derived index, answer with source-of-truth design.
The source-of-truth design answer includes Markdown, source of truth, Milvus, derived index, rebuild, and vendor lock-in.
Markdown avoids vendor lock-in because it is human-readable, Git-friendly, portable, and stable.

When asked what user workflows memsearch supports and how progressive recall works, answer with user workflows and progressive recall.
The user workflow answer includes debugging threads, decision rationale, feature history, code archaeology, L1, L2, and L3.
Progressive recall uses L1 search, L2 expand, and L3 transcript.

When asked how memsearch serves agent users and agent developers differently, answer with audience routes.
The audience route answer includes Agent Users, install a plugin, Agent Developers, CLI, Python API, and same CLI/API.
Agent Users install a plugin.
Agent Developers use the CLI and Python API.
All four platform plugins are built on the same CLI/API.
