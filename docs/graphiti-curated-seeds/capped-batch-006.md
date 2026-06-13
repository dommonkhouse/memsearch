<!--
MON-316 capped Graphiti relationship seed batch 006.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-006-sources.md
-->

# Embedding evaluation relationships

The Claude Code plugin default embedding model is ONNX bge-m3 int8.
The Claude Code plugin default embedding model uses `gpahal/bge-m3-onnx-int8`.
The ONNX bge-m3 int8 choice came from a real-world memory-retrieval benchmark.
The benchmark used 955 chunks and 2172 bilingual queries.
Recall@5 is the primary metric for the Claude Code plugin embedding benchmark.
ONNX bge-m3 int8 scored 0.776 Chinese Recall@5.
OpenAI text-embedding-3-small scored 0.717 Chinese Recall@5.
ONNX bge-m3 int8 outperformed OpenAI text-embedding-3-small on Chinese retrieval.
ONNX bge-m3 int8 lost only about 1 percent recall versus full-precision PyTorch bge-m3.
ONNX bge-m3 int8 reduced model size from 2.2 GB to 558 MB.
ONNX bge-m3 int8 dropped the `torch` dependency.
ONNX bge-m3 int8 needs no API key.
ONNX bge-m3 int8 is CPU-only.

# Embedding tradeoff relationships

BAAI/bge-m3 PyTorch is the full-precision bge-m3 baseline.
ONNX bge-m3 int8 keeps near-PyTorch quality with a smaller CPU runtime.
Ollama English-centric embedding models collapsed on Chinese retrieval in the benchmark.
`nomic-embed-text` and `mxbai-embed-large` were not safe as bilingual defaults.
Q5 quantization destroyed embedding quality for `Qwen3-Embedding-8B`.
OpenAI large was only slightly better than OpenAI small and was not worth the extra cost for memory retrieval.
Python API users are not affected by the Claude Code plugin switch to ONNX bge-m3 int8.
Python API default embedding remains OpenAI text-embedding-3-small.
Existing plugin users with OpenAI-indexed memory need force re-indexing after switching to ONNX.

# Python API indexing lifecycle relationships

The Python API entry point is the `MemSearch` class.
`MemSearch.index(force=False)` indexes markdown files into the vector store.
The Python API index is incremental by default.
The Python API index embeds only new or changed chunks by default.
The Python API index skips unchanged chunks through content-hash dedup.
`force=True` re-embeds all chunks even if unchanged.
Use `force=True` after switching embedding providers.
Python API stale cleanup removes chunks from deleted files.
Python API deleted-content cleanup removes old chunks when a section is removed from a file.
`MemSearch.index_file(path)` indexes a single markdown file.

# Python API agent loop and isolation relationships

A Python API agent loop starts by seeding knowledge into markdown.
The Python API agent loop recalls past memories with `mem.search`.
The Python API agent loop gives memory context to an LLM.
The Python API agent loop remembers by saving new memory content.
The Python API agent loop indexes saved memory with `mem.index`.
The Python API can use `mem.watch` to auto-index in the background.
Per-user memory isolation can use different `paths`.
Per-user memory isolation can use different `collection` names.
Per-user memory isolation can use different `milvus_uri` database files.
Different collections isolate agents that share the same backend.
Different Milvus Lite database files provide the strongest per-user isolation.
