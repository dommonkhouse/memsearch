<!--
MON-316 capped Graphiti relationship seed batch 010.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-010-sources.md
-->

# Product positioning and alternatives relationships

memsearch is an engine plus native plugins for Claude Code, OpenClaw, OpenCode, and Codex CLI.
memsearch covers coding CLI memory across four agent platforms.
Claude Code native memory is built in to Claude Code only and does not perform on-demand search.
Claude Code native memory fits when memory is tiny or project-instruction-like.
mem0 fits generic LLM applications more than coding CLI memory.
mem0 and Letta fit when the LLM should actively curate memory.
Letta fits when a full agent runtime or MemFS is needed.
qmd fits when the user just needs a local markdown search engine.
memsearch differs from mem0, Letta, and MemPalace because memsearch keeps Markdown as the source of truth.
memsearch differs from Claude Code native memory because memsearch retrieves on demand instead of loading the whole memory file every session.

# Source-of-truth design relationships

Markdown is the memsearch source of truth.
Milvus is a derived index in memsearch.
Milvus can be dropped and rebuilt from Markdown with `memsearch index`.
Markdown memory files are human-readable, Git-friendly, portable, and stable.
Opaque database source-of-truth storage creates vendor lock-in, migration costs, and fragility.
The memsearch vector store is an acceleration layer, not the canonical memory store.
MemSearch design is inspired by OpenClaw memory layout, chunk IDs, content-hash dedup, compact target, source-of-truth policy, and watch debounce.

# Agent user workflow relationships

Agent users use memsearch to resume debugging threads.
Agent users use memsearch to recover decision rationale.
Agent users use memsearch to trace feature history.
Agent users use memsearch for code archaeology before changing modules, config, or workflows.
Agent users use memsearch to find the right previous session to resume.
Agent users use memsearch to carry context across Claude Code, Codex CLI, OpenClaw, and OpenCode.
Progressive recall starts at L1 search, then L2 expand, then L3 transcript.
Simple questions can stop at L1 search.
Complex questions can drill into L2 expand and L3 transcript.

# Audience route relationships

Agent Users install a plugin and get persistent memory with zero commands to learn and zero manual saving.
Agent Developers build memory into agents with the memsearch CLI and Python API.
The memsearch CLI provides `memsearch index`, `memsearch search`, `memsearch expand`, and `memsearch watch`.
All four platform plugins are built on the same CLI/API.
Plugin capture follows conversation to LLM summary to daily markdown to `memsearch index`.
Plugin recall follows `memsearch search` to `memsearch expand` to parse-transcript.
