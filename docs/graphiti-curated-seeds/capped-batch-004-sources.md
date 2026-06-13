# Batch 004 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti architecture recall tuning.

## Source safety decisions

- `docs/architecture.md`: safe to distil, unsafe for direct ingestion. It contains broad architecture tables, Mermaid diagrams, operational examples, and deployment detail that would be noisy as unfiltered graph facts.
- `docs/cli.md`: safe to distil, unsafe for direct ingestion. It contains command reference examples, flags, and local operational routes that should not all become relationship facts.
- `docs/troubleshooting.md`: safe to distil for negative and diagnostic facts, unsafe for direct ingestion. It includes reset and recovery commands that should not be surfaced without context.
- `docs/getting-started.md`: safe to distil, unsafe for direct ingestion. It includes tutorial examples, placeholder names, and illustrative agent flows that are too broad for this capped batch.

## Statement evidence

- Statement: Claude Code capture uses a Stop hook and Haiku.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:32-33`.
- Statement: OpenClaw capture uses `agent_end`.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:32-33`.
- Statement: OpenCode capture uses a SQLite daemon.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:32-33`.
- Statement: Codex CLI capture uses a Stop hook and Codex.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:32-33`.
- Statement: All platform capture writes daily markdown memory files.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:32-33`.
- Statement: Daily markdown memory files feed the shared Milvus index.
  Evidence: `docs/architecture.md:13-26`; `docs/architecture.md:40-42`.
- Statement: Platform plugins can share `milvus_uri` and `collection`.
  Evidence: `docs/architecture.md:32-33`.
- Statement: Per-project collections isolate memories by project.
  Evidence: `docs/architecture.md:207-209`.
- Statement: MemSearch scans Markdown files with Scanner.
  Evidence: `docs/architecture.md:55-57`; `docs/architecture.md:332-384`; `docs/cli.md:325-385`.
- Statement: Scanner sends Markdown sections to Chunker.
  Evidence: `docs/architecture.md:55-57`; `docs/architecture.md:80-108`; `docs/architecture.md:332-384`.
- Statement: Chunker splits by headings.
  Evidence: `docs/architecture.md:80-108`.
- Statement: Chunker uses paragraph fallback for oversized sections.
  Evidence: `docs/architecture.md:80-108`.
- Statement: MemSearch hashes chunk content with SHA-256.
  Evidence: `docs/architecture.md:126-151`; `docs/getting-started.md:61-87`.
- Statement: MemSearch uses composite chunk IDs from source path, line range, content hash, and embedding model.
  Evidence: `docs/architecture.md:126-151`.
- Statement: MemSearch embeds only new or changed chunks.
  Evidence: `docs/architecture.md:55-57`; `docs/architecture.md:126-151`; `docs/cli.md:325-385`.
- Statement: MemSearch deletes stale chunks for deleted files.
  Evidence: `docs/architecture.md:55-57`; `docs/cli.md:325-385`; `docs/cli.md:465-511`.
- Statement: MemSearch stores dense vectors and BM25 sparse vectors in Milvus.
  Evidence: `docs/architecture.md:155-183`; `docs/cli.md:389-461`.
- Statement: MemSearch search uses dense vector search, BM25 sparse search, and RRF reranking.
  Evidence: `docs/architecture.md:40-42`; `docs/architecture.md:155-183`; `docs/cli.md:389-461`.
- Statement: MemSearch configuration priority is built-in defaults, then `~/.memsearch/config.toml`, then `.memsearch.toml`, then CLI flags.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: CLI flags have highest priority.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: API keys are read from environment variables.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: API keys are never written to config files.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: `memsearch index` scans markdown into Milvus.
  Evidence: `docs/cli.md:18-49`; `docs/cli.md:325-385`.
- Statement: `memsearch search` searches indexed chunks.
  Evidence: `docs/cli.md:18-49`; `docs/cli.md:389-461`.
- Statement: `memsearch expand` shows the full section around a chunk.
  Evidence: `docs/architecture.md:213-247`; `docs/cli.md:18-49`.
- Statement: `memsearch watch` monitors markdown changes and auto-indexes.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:18-49`; `docs/cli.md:465-511`.
- Statement: `memsearch compact` compresses indexed chunks into a summary.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:18-49`; `docs/cli.md:515-560`.
- Statement: Compact writes to `memory/YYYY-MM-DD.md`.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:515-560`.
- Statement: The file watcher re-indexes compact summaries.
  Evidence: `docs/architecture.md:67-70`; `docs/architecture.md:332-384`; `docs/cli.md:465-560`.
- Statement: Markdown remains the source of truth.
  Evidence: `docs/architecture.md:332-384`; `docs/architecture.md:388-415`; `docs/getting-started.md:87-88`; `docs/troubleshooting.md:83-97`.
- Statement: Milvus remains a derived index.
  Evidence: `docs/architecture.md:332-384`; `docs/getting-started.md:87-88`; `docs/troubleshooting.md:83-97`.
- Statement: MemSearch Configuration Priority Chain includes built-in defaults, global config file, project config file, and CLI flags.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: The global config file is `~/.memsearch/config.toml`.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: The project config file is `.memsearch.toml`.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: CLI flags override project config file, project config file overrides global config file, and global config file overrides built-in defaults.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: MemSearch API key policy reads API keys from environment variables and never writes API keys to config files.
  Evidence: `docs/architecture.md:251-269`; `docs/cli.md:80-89`.
- Statement: MemSearch source of truth is Markdown, not Milvus.
  Evidence: `docs/architecture.md:332-384`; `docs/getting-started.md:87-88`; `docs/troubleshooting.md:83-97`.
- Statement: Milvus can be rebuilt from Markdown.
  Evidence: `docs/troubleshooting.md:83-97`.
- Statement: MemSearch Command Role Map includes `memsearch index`, `memsearch search`, `memsearch expand`, `memsearch watch`, and `memsearch compact`.
  Evidence: `docs/cli.md:18-49`; `docs/cli.md:325-560`.
- Statement: `memsearch index` indexes Markdown files into Milvus.
  Evidence: `docs/cli.md:325-385`.
- Statement: `memsearch search` searches indexed chunks.
  Evidence: `docs/cli.md:389-461`.
- Statement: `memsearch expand` shows the full section around a chunk.
  Evidence: `docs/architecture.md:213-247`; `docs/cli.md:18-49`.
- Statement: `memsearch watch` monitors Markdown changes and auto-indexes them.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:465-511`.
- Statement: `memsearch compact` compresses indexed chunks into a summary.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:515-560`.
- Statement: `memsearch compact` writes a daily markdown summary to `memory/YYYY-MM-DD.md`.
  Evidence: `docs/architecture.md:67-70`; `docs/cli.md:515-560`.
- Statement: `memsearch watch` detects and re-indexes daily markdown summary changes.
  Evidence: `docs/architecture.md:67-70`; `docs/architecture.md:332-384`; `docs/cli.md:465-560`.
