# Capped batch 017: Superpowers plan relationship boundaries

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils durable relationships from Superpowers plan files.
It does not ingest `.memsearch/memory` or raw task transcripts.

## Graphiti sidecar boundary relationships

Graphiti was planned as an optional derived knowledge-graph recall layer for MemSearch.
Graphiti must not replace Markdown, Milvus, or existing memory-recall behaviour.
Markdown remains canonical for MemSearch.
Milvus remains the rebuildable semantic and BM25 index for MemSearch.
The first Graphiti version exposes explicit CLI commands for graph indexing and graph search only.
Automatic prompt injection must wait until the Graphiti pilot proves useful and stable.

## Kuzu deferral relationships

FalkorDB stayed the first Graphiti backend for the MemSearch pilot.
Kuzu was deferred for the MemSearch Graphiti pilot.
Kuzu was deferred because the KuzuDB repo was archived.
Kuzu was also deferred because current Graphiti issue traffic included Kuzu add-episode crashes.
The Kuzu decision trail should be revisited only after the FalkorDB pilot.

## Capped ingest safety relationships

Graphiti capped ingest uses group `ms_memsearch_active_curated_v1`.
Graphiti capped ingest uses manifest `.memsearch/graphiti-curated-manifest.json`.
Graphiti capped ingest must use dry-run, cap, manifest checkpoint, evaluation, and rollback at every batch.
Graphiti capped ingest must not perform full `.memsearch/memory` ingestion without dry-run, cap, review, and explicit approval.
Graphiti capped ingest rollback clears only group `ms_memsearch_active_curated_v1`.
Graphiti capped ingest rollback restores the curated manifest from a pre-batch checkpoint.

## Chat backfill source-normalisation relationships

The MemSearch chat backfill plan uses a source-normalisation pipeline.
The chat backfill pipeline converts transcript and export files into canonical markdown grouped by machine, source, and month.
The chat backfill pipeline writes manifests for repeatable incremental runs.
The chat backfill pipeline indexes generated markdown with the existing `memsearch index` CLI.
For chat backfill, generated markdown and manifests are the source of truth.
For chat backfill, Milvus remains a rebuildable derived index.

## Manus three-lane recall relationships

Manus MemSearch closeout uses three lanes: raw Manus export, sanitised full Markdown, and compact session cards.
Raw Manus export is the Manus source-of-truth lane.
Sanitised full Markdown is the Manus evidence lane.
Compact session cards are the practical MemSearch recall layer for Manus.
Canonical Manus ingestion must use the compact card lane, not raw event logs.
Raw event-log indexing was rejected because local ONNX embedding was too slow and raw tool payloads made low-value embeddings.

## Source freshness scheduling relationships

Memory source freshness refreshes Manus into MemSearch weekly and Linear into MemSearch daily.
Source freshness keeps Markdown as the canonical memory source and Milvus as a rebuildable index.
Source freshness writes Linear and Manus source cards into `.memsearch/memory/`.
Source freshness scheduler definitions are dry-run artefacts until explicit approval.
Linear source freshness should use `LINEAR_API_KEY` bearer-token GraphQL.
Manus weekly sync must use client-side diff where server-side updated filtering is unavailable.
Manus weekly sync must refuse silent full export when state is missing or timestamps are unreliable.
