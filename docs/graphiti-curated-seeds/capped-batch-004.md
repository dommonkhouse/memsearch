<!--
MON-316 capped Graphiti relationship seed batch 004.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-004-sources.md
-->

# Platform capture relationships

Claude Code capture uses a Stop hook and Haiku.
OpenClaw capture uses `agent_end`.
OpenCode capture uses a SQLite daemon.
Codex CLI capture uses a Stop hook and Codex.
All platform capture writes daily markdown memory files.
Daily markdown memory files feed the shared Milvus index.
Platform plugins can share `milvus_uri` and `collection`.
Per-project collections isolate memories by project.

# Indexing and retrieval relationships

MemSearch scans Markdown files with Scanner.
Scanner sends Markdown sections to Chunker.
Chunker splits by headings.
Chunker uses paragraph fallback for oversized sections.
MemSearch hashes chunk content with SHA-256.
MemSearch uses composite chunk IDs from source path, line range, content hash, and embedding model.
MemSearch embeds only new or changed chunks.
MemSearch deletes stale chunks for deleted files.
MemSearch stores dense vectors and BM25 sparse vectors in Milvus.
MemSearch search uses dense vector search, BM25 sparse search, and RRF reranking.

# Configuration, CLI, watch, and compact relationships

MemSearch configuration priority is built-in defaults, then `~/.memsearch/config.toml`, then `.memsearch.toml`, then CLI flags.
CLI flags have highest priority.
API keys are read from environment variables.
API keys are never written to config files.
`memsearch index` scans markdown into Milvus.
`memsearch search` searches indexed chunks.
`memsearch expand` shows the full section around a chunk.
`memsearch watch` monitors markdown changes and auto-indexes.
`memsearch compact` compresses indexed chunks into a summary.
Compact writes to `memory/YYYY-MM-DD.md`.
The file watcher re-indexes compact summaries.
Markdown remains the source of truth.
Milvus remains a derived index.
