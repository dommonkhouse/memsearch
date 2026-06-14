# Batch 010 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti product positioning and user/developer relationship tuning.

## Source safety decisions

- `docs/design-philosophy.md`: safe to distil, unsafe for direct ingestion. It contains diagrams and explanatory prose; Batch 010 only needs source-of-truth, cross-platform, hybrid recall, progressive disclosure, Milvus, and OpenClaw inspiration relationships.
- `docs/home/why.md`: safe to distil, unsafe for direct ingestion. It contains concise product positioning and feature bullets; Batch 010 only needs user/developer audience and feature relationships.
- `docs/home/comparison.md`: safe to distil, unsafe for direct ingestion. It contains competitor tables and references; Batch 010 only needs alternatives-fit and differentiation relationships.
- `docs/home/for-users.md`: safe to distil, unsafe for direct ingestion. It contains user-facing examples and platform table; Batch 010 only needs workflow and progressive recall relationships.
- `docs/home/for-developers.md`: safe to distil, unsafe for direct ingestion. It contains install snippets and code examples; Batch 010 only needs CLI/API and plugin pipeline relationships.

## Statement evidence

- Statement: memsearch covers Claude Code, OpenClaw, OpenCode, and Codex CLI in one project.
  Evidence: `docs/home/why.md:3-7`; `docs/home/comparison.md:46-54`; `docs/design-philosophy.md:38-69`.
- Statement: Claude Code native memory is built in to Claude Code only and lacks on-demand search.
  Evidence: `docs/home/comparison.md:9-16`; `docs/home/comparison.md:20-40`.
- Statement: Claude Code native memory fits when memory is tiny or project-instruction-like.
  Evidence: `docs/home/comparison.md:56-63`.
- Statement: mem0 fits generic LLM applications, and mem0 or Letta fit when LLM memory curation is wanted.
  Evidence: `docs/home/comparison.md:56-63`.
- Statement: Letta fits full agent runtime or MemFS needs.
  Evidence: `docs/home/comparison.md:56-63`.
- Statement: qmd fits local markdown search engine needs.
  Evidence: `docs/home/comparison.md:56-63`.
- Statement: Markdown is the memsearch source of truth and Milvus is a derived index.
  Evidence: `docs/design-philosophy.md:7-35`; `docs/home/why.md:16-20`; `docs/home/comparison.md:46-54`.
- Statement: Markdown memory files are human-readable, Git-friendly, portable, and low lock-in.
  Evidence: `docs/design-philosophy.md:21-35`.
- Statement: Opaque database source-of-truth storage creates vendor lock-in and fragility.
  Evidence: `docs/design-philosophy.md:28-35`.
- Statement: MemSearch design follows OpenClaw memory layout, chunk IDs, dedup, compact target, source-of-truth policy, and watch debounce.
  Evidence: `docs/design-philosophy.md:143-156`.
- Statement: Agent users use memsearch for debugging threads, decision rationale, feature history, code archaeology, session resumption, and cross-agent context.
  Evidence: `docs/home/for-users.md:5-13`.
- Statement: Progressive recall uses L1 search, L2 expand, and L3 transcript.
  Evidence: `docs/design-philosophy.md:85-109`; `docs/home/for-users.md:33-41`.
- Statement: Agent Users install a plugin and get persistent memory with zero commands and zero manual saving.
  Evidence: `docs/home/why.md:9-14`; `docs/home/for-users.md:23-32`.
- Statement: Agent Developers use the CLI and Python API to build memory into agents.
  Evidence: `docs/home/why.md:9-14`; `docs/home/for-developers.md:1-4`; `docs/home/for-developers.md:43-63`.
- Statement: All four platform plugins are built on the same CLI/API, with capture from conversation to summary to daily markdown to index, and recall from search to expand to parse-transcript.
  Evidence: `docs/home/for-developers.md:54-63`.
