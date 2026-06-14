# Batch 011 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti docs-navigation, configuration, platform comparison, and framework integration relationship tuning.

## Source safety decisions

- `docs/home/configuration.md`: safe to distil, unsafe for direct ingestion. It contains config examples and links; Batch 011 only needs plugin summarization routing, config priority, and maintenance-task relationships.
- `docs/integrations.md`: safe to distil, unsafe for direct ingestion. It contains long code examples; Batch 011 only needs framework integration relationships for LangChain, LangGraph, LlamaIndex, and CrewAI.
- `docs/platforms/index.md`: safe to distil, unsafe for direct ingestion. It contains comparison tables and diagrams; Batch 011 only needs platform comparison, shared architecture, and sharing/isolation relationships.
- `docs/index.md`: safe to distil, unsafe for direct ingestion. It contains homepage-style product docs and install snippets; Batch 011 only needs cross-platform sharing, top-level platform routes, embedding, backend, and source-of-truth relationships.

## Statement evidence

- Statement: Plugin summarization routing is plugin-specific, preserves native/default summarizers when provider is empty or `native`, and does not fall back to `llm.model`.
  Evidence: `docs/home/configuration.md:73-96`; `docs/platforms/index.md:21-31`.
- Statement: A memsearch-managed summarizer requires defining `llm.providers.<name>` and setting `plugins.<platform>.summarize.provider` to that provider.
  Evidence: `docs/home/configuration.md:82-91`; `docs/platforms/index.md:26-30`.
- Statement: A plugin native model can be overridden with `plugins.<platform>.summarize.model`.
  Evidence: `docs/home/configuration.md:73-81`; `docs/platforms/index.md:21-25`.
- Statement: Automatic capture can be disabled per project with `plugins.<platform>.summarize.enabled false --project`.
  Evidence: `docs/home/configuration.md:96-101`.
- Statement: Claude Code uses shell hooks, SKILL.md recall, Claude Code JSONL, and marketplace installation.
  Evidence: `docs/platforms/index.md:7-19`; `docs/index.md:17-31`.
- Statement: OpenClaw uses TypeScript registerTool, agent_end hook, memory_search tools, OpenClaw JSONL, and hook permissions.
  Evidence: `docs/platforms/index.md:7-19`; `docs/index.md:33-46`.
- Statement: OpenCode uses an npm plugin, SQLite daemon capture, memory_search tools, and OpenCode SQLite transcript format.
  Evidence: `docs/platforms/index.md:7-19`; `docs/index.md:48-56`.
- Statement: Codex CLI uses shell hooks, SKILL.md recall, rollout JSONL transcript format, and `install.sh`.
  Evidence: `docs/platforms/index.md:7-19`; `docs/index.md:58-68`.
- Statement: LangChain integration wraps MemSearch in a BaseRetriever and returns Documents with source, heading, and score metadata.
  Evidence: `docs/integrations.md:7-49`.
- Statement: LangGraph integration exposes search_memory as a tool for a ReAct agent.
  Evidence: `docs/integrations.md:74-121`.
- Statement: LlamaIndex integration implements a BaseRetriever returning NodeWithScore objects.
  Evidence: `docs/integrations.md:125-177`.
- Statement: CrewAI integration registers search_memory as a CrewAI tool.
  Evidence: `docs/integrations.md:187-236`.
- Statement: All plugins write standard markdown memory files and derive collection names from the project directory using the same algorithm.
  Evidence: `docs/platforms/index.md:75-103`; `docs/index.md:70-81`.
- Statement: Same project directory means same collection and shared memories; different project directories remain isolated.
  Evidence: `docs/platforms/index.md:96-103`; `docs/index.md:70-81`.
