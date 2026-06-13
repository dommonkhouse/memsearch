# Batch 002 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti ingest expansion.

## Source safety decisions

- `docs/platforms/codex/memory-recall.md`: safe to distil, unsafe for direct ingestion. It is current platform documentation, but includes examples and debugging commands that should not become graph facts.
- `docs/platforms/claude-code/memory-recall.md`: safe to distil, unsafe for direct ingestion. It is current platform documentation, but includes illustrative examples and comparisons that are better represented as explicit seed facts.
- `docs/platforms/openclaw/memory-tools.md`: safe to distil, unsafe for direct ingestion. It is current platform documentation, but includes example cache stories and comparison tables that could add noisy entities.
- `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md`: safe to distil. The file is only seven lines and records a current relationship-extraction guardrail. It is still distilled to avoid ingesting the concrete bad edge examples as facts.

## Statement evidence

- Statement: Codex memory recall runs in the main conversation context.
  Evidence: `docs/platforms/codex/memory-recall.md:91-106`.
- Statement: Codex memory recall does not use a forked subagent context.
  Evidence: `docs/platforms/codex/memory-recall.md:91-106`.
- Statement: Claude Code memory recall runs in a forked subagent context.
  Evidence: `docs/platforms/claude-code/memory-recall.md:1-4`; `docs/platforms/claude-code/memory-recall.md:129-142`.
- Statement: Claude Code memory recall keeps intermediate search and expansion results out of the main conversation.
  Evidence: `docs/platforms/claude-code/memory-recall.md:26-32`; `docs/platforms/claude-code/memory-recall.md:129-142`.
- Statement: OpenClaw memory tools target the current agent memory directory and Milvus collection.
  Evidence: `docs/platforms/openclaw/memory-tools.md:1-4`.
- Statement: OpenClaw memory_search runs MemSearch search over indexed memories.
  Evidence: `docs/platforms/openclaw/memory-tools.md:7-13`.
- Statement: OpenClaw memory_get expands a MemSearch chunk into the full markdown section.
  Evidence: `docs/platforms/openclaw/memory-tools.md:7-13`.
- Statement: OpenClaw memory_transcript reads the original OpenClaw JSONL transcript.
  Evidence: `docs/platforms/openclaw/memory-tools.md:7-13`.
- Statement: MemSearch memory recall starts with L1 search.
  Evidence: `docs/platforms/codex/memory-recall.md:22-43`; `docs/platforms/claude-code/memory-recall.md:7-32`; `docs/platforms/openclaw/memory-tools.md:33-58`.
- Statement: MemSearch memory recall uses L2 expand for full markdown section context.
  Evidence: `docs/platforms/codex/memory-recall.md:22-55`; `docs/platforms/claude-code/memory-recall.md:7-32`; `docs/platforms/openclaw/memory-tools.md:33-58`.
- Statement: MemSearch memory recall uses L3 transcript or rollout drill-down when exact original conversation detail is needed.
  Evidence: `docs/platforms/codex/memory-recall.md:22-43`; `docs/platforms/claude-code/memory-recall.md:7-32`; `docs/platforms/openclaw/memory-tools.md:33-58`.
- Statement: MemSearch hybrid search combines dense search with BM25 and RRF fusion.
  Evidence: `docs/platforms/claude-code/memory-recall.md:129-140`; `docs/platforms/codex/memory-recall.md:39-43`.
- Statement: BM25 helps MemSearch catch exact identifiers that dense-only memory search can miss.
  Evidence: `docs/platforms/openclaw/memory-tools.md:92-123`; `docs/platforms/codex/memory-recall.md:110-112`.
- Statement: Milvus is the MemSearch vector backend for hybrid recall.
  Evidence: `docs/platforms/openclaw/memory-tools.md:92-123`; `docs/platforms/codex/memory-recall.md:106`.
- Statement: Plain markdown files remain the editable source storage for MemSearch memories.
  Evidence: `docs/platforms/claude-code/memory-recall.md:106-125`; `docs/platforms/openclaw/memory-tools.md:92-123`.
- Statement: Open Brain graph extraction must not infer Dominic's own client relationships from advisory conversations about another person's market.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:1-7`.
- Statement: Open Brain relation filters reject misleading client_of edges from advisory patterns.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:3-7`.
- Statement: Open Brain relation filters reject misleading works_on edges from advisory patterns.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:3-7`.
- Statement: Discussion edges may describe what Dominic discussed.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:7`.
- Statement: Relationship edges that imply Dominic did the work need stronger evidence than advice or discussion.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:7`.
- Statement: Relationship edges that imply Dominic served the client need stronger evidence than advice or discussion.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:7`.
- Statement: Relationship edges that imply Dominic owned the project need stronger evidence than advice or discussion.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/open-brain-knowledge-graph.md:7`.
