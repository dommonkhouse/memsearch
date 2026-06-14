# Capped batch 017 correction relationships

Reviewed on 2026-06-14 for MON-316 capped Graphiti Superpowers-plan tuning.

## Graphiti sidecar correction relationships

Graphiti sidecar boundary answer includes Graphiti, optional derived, Markdown, canonical, Milvus, explicit CLI, and prompt injection.
Graphiti is optional and derived for MemSearch.
Markdown is canonical for MemSearch.
Milvus is the primary rebuildable index for MemSearch.
Explicit CLI graph commands come before automatic prompt injection.

## Kuzu deferral correction relationships

Kuzu deferral answer includes Kuzu, deferred, archived, crash, FalkorDB, and pilot.
Kuzu was deferred for the MemSearch Graphiti pilot.
KuzuDB archive status contributed to the deferral.
Kuzu add-episode crash reports contributed to the deferral.
FalkorDB stayed first for the contained Graphiti pilot.

## Capped ingest rollback correction relationships

Capped ingest safety answer includes `ms_memsearch_active_curated_v1`, `.memsearch/graphiti-curated-manifest.json`, dry-run, cap, manifest checkpoint, rollback, and no full `.memsearch/memory` ingestion.
The capped ingest group is `ms_memsearch_active_curated_v1`.
The capped ingest manifest is `.memsearch/graphiti-curated-manifest.json`.
Rollback clears only the curated group and restores the manifest checkpoint.

## Chat backfill correction relationships

Chat backfill source-normalisation answer includes source-normalisation, canonical markdown, manifest, incremental, Milvus, and derived index.
The chat backfill pipeline converts exports and transcripts into canonical markdown.
The chat backfill manifest enables repeatable incremental runs.
Milvus is a rebuildable derived index for chat backfill.

## Manus recall correction relationships

Manus three-lane recall answer includes raw Manus export, sanitised full Markdown, compact session cards, practical MemSearch recall layer, raw event logs, too slow, and low-value embeddings.
Raw Manus export is the source-of-truth lane.
Sanitised full Markdown is the evidence lane.
Compact session cards are the practical MemSearch recall lane.
Raw event-log indexing was rejected as too slow with local ONNX and too noisy because of low-value embeddings.

## Source freshness correction relationships

Source freshness scheduling answer includes Linear, daily, Manus, weekly, Markdown, source cards, dry-run, client-side diff, and refuse a silent full export.
Linear source freshness is daily.
Manus source freshness is weekly.
Source freshness writes source cards into `.memsearch/memory/`.
Manus weekly sync uses client-side diff and refuses silent full export when state is unsafe.
