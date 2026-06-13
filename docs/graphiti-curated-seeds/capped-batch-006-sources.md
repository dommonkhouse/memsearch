# Batch 006 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti embedding evaluation and Python API lifecycle recall tuning.

## Source safety decisions

- `docs/home/embedding-evaluation.md`: safe to distil, unsafe for direct ingestion. It contains benchmark tables, raw model rankings, and compatibility commands that would be noisy as raw graph facts.
- `docs/python-api.md`: safe to distil, unsafe for direct ingestion. It contains long code examples and API reference detail; Batch 006 only needs lifecycle and isolation relationships.

## Statement evidence

- Statement: The Claude Code plugin default embedding model is ONNX bge-m3 int8 and uses `gpahal/bge-m3-onnx-int8`.
  Evidence: `docs/home/embedding-evaluation.md:3-5`; `docs/home/embedding-evaluation.md:100-109`; `docs/home/embedding-evaluation.md:129-133`.
- Statement: The embedding benchmark used 955 chunks and 2172 bilingual queries.
  Evidence: `docs/home/embedding-evaluation.md:5`; `docs/home/embedding-evaluation.md:18-30`.
- Statement: Recall@5 is the primary metric for the Claude Code plugin embedding benchmark.
  Evidence: `docs/home/embedding-evaluation.md:53-61`.
- Statement: ONNX bge-m3 int8 scored 0.776 Chinese Recall@5 and OpenAI text-embedding-3-small scored 0.717.
  Evidence: `docs/home/embedding-evaluation.md:63-73`; `docs/home/embedding-evaluation.md:100-109`.
- Statement: ONNX bge-m3 int8 lost about 1 percent recall versus full-precision PyTorch bge-m3 while reducing model size to 558 MB and dropping the `torch` dependency.
  Evidence: `docs/home/embedding-evaluation.md:5`; `docs/home/embedding-evaluation.md:83-89`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: ONNX bge-m3 int8 needs no API key and is CPU-only.
  Evidence: `docs/home/embedding-evaluation.md:11-16`; `docs/home/embedding-evaluation.md:100-109`; `docs/home/embedding-evaluation.md:129-133`.
- Statement: BAAI/bge-m3 PyTorch is the full-precision baseline and ONNX bge-m3 int8 keeps near-PyTorch quality with smaller CPU runtime.
  Evidence: `docs/home/embedding-evaluation.md:83-89`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: Ollama English-centric embedding models collapsed on Chinese retrieval and were not safe as bilingual defaults.
  Evidence: `docs/home/embedding-evaluation.md:76-81`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: Q5 quantization destroyed embedding quality for `Qwen3-Embedding-8B`.
  Evidence: `docs/home/embedding-evaluation.md:76-81`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: OpenAI large was only slightly better than OpenAI small and was not worth the extra cost for memory retrieval.
  Evidence: `docs/home/embedding-evaluation.md:69-73`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: Python API users are not affected by the Claude Code plugin switch and Python API default remains OpenAI text-embedding-3-small.
  Evidence: `docs/home/embedding-evaluation.md:111-121`; `docs/python-api.md:21-52`.
- Statement: Existing plugin users with OpenAI-indexed memory need force re-indexing after switching to ONNX.
  Evidence: `docs/home/embedding-evaluation.md:111-121`.
- Statement: The Python API entry point is `MemSearch`.
  Evidence: `docs/python-api.md:1-19`.
- Statement: `MemSearch.index(force=False)` indexes markdown files into the vector store.
  Evidence: `docs/python-api.md:69-82`.
- Statement: Python API indexing is incremental, embeds only new or changed chunks, and skips unchanged chunks through content-hash dedup.
  Evidence: `docs/python-api.md:83-96`.
- Statement: `force=True` re-embeds all chunks and should be used after switching embedding providers.
  Evidence: `docs/python-api.md:79-96`.
- Statement: Python API stale cleanup removes chunks for deleted files and removed sections.
  Evidence: `docs/python-api.md:83-96`.
- Statement: `MemSearch.index_file(path)` indexes a single markdown file.
  Evidence: `docs/python-api.md:100-114`.
- Statement: A Python API agent loop recalls with `mem.search`, gives context to an LLM, saves memory, and indexes with `mem.index`.
  Evidence: `docs/python-api.md:238-290`; `docs/python-api.md:293-377`.
- Statement: The Python API can use `mem.watch` to auto-index in the background.
  Evidence: `docs/python-api.md:199-224`; `docs/python-api.md:282-286`.
- Statement: Per-user isolation can use different `paths`, `collection` names, and `milvus_uri` database files.
  Evidence: `docs/python-api.md:381-415`.
- Statement: `gpahal/bge-m3-onnx-int8` is the named ONNX bge-m3 int8 model and has a 558 MB model size.
  Evidence: `docs/home/embedding-evaluation.md:3-5`; `docs/home/embedding-evaluation.md:50-51`; `docs/home/embedding-evaluation.md:100-109`.
- Statement: The MemSearch embedding benchmark was bilingual and Q5 quantization was a failure mode for `Qwen3-Embedding-8B`.
  Evidence: `docs/home/embedding-evaluation.md:18-30`; `docs/home/embedding-evaluation.md:76-81`; `docs/home/embedding-evaluation.md:91-99`.
- Statement: The Python API force re-index control is `force=True`.
  Evidence: `docs/python-api.md:69-96`.
- Statement: The Python API agent loop has a save memory step before `mem.index`.
  Evidence: `docs/python-api.md:238-290`; `docs/python-api.md:293-377`.
- Statement: MemSearch stale cleanup deletes stale chunks during the next index run when an indexed file no longer exists.
  Evidence: `docs/cli.md:381-385`.
