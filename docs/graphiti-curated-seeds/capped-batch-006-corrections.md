<!--
MON-316 capped Graphiti relationship seed batch 006 corrective reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-006-sources.md
-->

# Embedding evaluation anchor relationships

`gpahal/bge-m3-onnx-int8` is the named ONNX bge-m3 int8 model in the MemSearch embedding evaluation.
The MemSearch embedding benchmark is bilingual.
The MemSearch embedding benchmark uses Chinese and English queries.
ONNX bge-m3 int8 has 558 MB model size.
ONNX bge-m3 int8 combines 558 MB model size with no API key and no `torch` dependency.
Q5 quantization is a MemSearch embedding evaluation failure mode.
Q5 quantization destroyed embedding quality for `Qwen3-Embedding-8B`.

# Python API lifecycle anchor relationships

`force=True` is the Python API force re-index control.
`force=True` re-embeds all Python API chunks even if unchanged.
`force=True` should be used after switching embedding providers.
Content-hash dedup is bypassed by `force=True`.
The Python API agent loop has a save memory step.
The Python API agent loop saves new memory content before calling `mem.index`.

# Stale chunk anchor relationships

MemSearch stale cleanup deletes stale chunks during the next index run.
Stale chunks are deleted when a previously indexed file no longer exists.
