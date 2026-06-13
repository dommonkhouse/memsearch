<!--
MON-316 capped Graphiti relationship seed batch 002.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-002-sources.md
-->

# MemSearch memory recall platform relationships

Codex memory recall runs in the main conversation context.
Codex memory recall does not use a forked subagent context.
Claude Code memory recall runs in a forked subagent context.
Claude Code memory recall keeps intermediate search and expansion results out of the main conversation.
OpenClaw memory tools target the current agent memory directory and Milvus collection.
OpenClaw memory_search runs MemSearch search over indexed memories.
OpenClaw memory_get expands a MemSearch chunk into the full markdown section.
OpenClaw memory_transcript reads the original OpenClaw JSONL transcript.

# MemSearch progressive recall and backend relationships

MemSearch memory recall starts with L1 search.
MemSearch memory recall uses L2 expand for full markdown section context.
MemSearch memory recall uses L3 transcript or rollout drill-down when exact original conversation detail is needed.
MemSearch hybrid search combines dense search with BM25 and RRF fusion.
BM25 helps MemSearch catch exact identifiers that dense-only memory search can miss.
Milvus is the MemSearch vector backend for hybrid recall.
Plain markdown files remain the editable source storage for MemSearch memories.

# Open Brain relationship extraction guardrails

Open Brain graph extraction must not infer Dominic's own client relationships from advisory conversations about another person's market.
Open Brain relation filters reject misleading client_of edges from advisory patterns.
Open Brain relation filters reject misleading works_on edges from advisory patterns.
Discussion edges may describe what Dominic discussed.
Relationship edges that imply Dominic did the work need stronger evidence than advice or discussion.
Relationship edges that imply Dominic served the client need stronger evidence than advice or discussion.
Relationship edges that imply Dominic owned the project need stronger evidence than advice or discussion.
