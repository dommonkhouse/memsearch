<!--
MON-316 capped Graphiti relationship seed batch 004 command and watch reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-004-sources.md
-->

# MemSearch command role map

MemSearch Command Role Map is a CLI relationship map.
MemSearch Command Role Map includes `memsearch index`.
`memsearch index` indexes Markdown files into Milvus.
MemSearch Command Role Map includes `memsearch search`.
`memsearch search` searches indexed chunks.
MemSearch Command Role Map includes `memsearch expand`.
`memsearch expand` shows the full section around a chunk.
MemSearch Command Role Map includes `memsearch watch`.
`memsearch watch` monitors Markdown changes and auto-indexes them.
MemSearch Command Role Map includes `memsearch compact`.
`memsearch compact` compresses indexed chunks into a summary.

# MemSearch watch compact loop

MemSearch Watch Compact Loop connects `memsearch compact` to `memsearch watch`.
`memsearch compact` writes a daily markdown summary.
The daily markdown summary path is `memory/YYYY-MM-DD.md`.
`memsearch watch` detects daily markdown summary changes.
`memsearch watch` re-indexes daily markdown summaries into Milvus.
The file watcher re-indexes compact summaries.
