# Capped batch 020: MacBook pilot historical boundary

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils historical MacBook pilot boundaries.
It does not ingest `.memsearch/memory` or raw task transcripts.

## Historical MacBook pilot relationships

The MacBook Graphiti pilot docs are historical.
The current verified Graphiti runtime route is the Mac Mini Tailscale Serve route in `docs/graphiti-falkordb.md`.
The MacBook local route used Colima and Docker CLI on `Dominic's Macbook`.
The MacBook local route used the active default `colima` Docker context.
The MacBook local route planned Graphiti MCP on `127.0.0.1:8018`.
The MacBook local route planned endpoint `http://127.0.0.1:8018/mcp/`.
The MacBook local route planned group `ms_memsearch_ae2d4f9b`.
The MacBook local route planned manifest `.memsearch/graphiti-manifest.json`.
The MacBook local route is not the current production Graphiti route.
The current production Graphiti route is `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018`.
The current curated Graphiti group is `ms_memsearch_active_curated_v1`.
The current curated manifest is `.memsearch/graphiti-curated-manifest.json`.

## Pilot preflight relationships

The 2026-06-11 21:08:49 BST MacBook preflight passed.
The passed MacBook preflight found Docker, Docker Compose, Colima, and `OPENAI_API_KEY`.
The passed MacBook preflight found ports `8018` and `6379` free.
The earlier 2026-06-11 11:21:43 BST MacBook preflight was blocked.
The blocked MacBook preflight found no local container/runtime route.
The blocked MacBook preflight should not proceed to Graphiti MCP protocol probing.
The blocked MacBook preflight should not implement a guessed client route.

## Historical sidecar boundaries

The MacBook pilot kept Markdown as the source of truth.
The MacBook pilot kept Milvus as the primary automatic recall index.
The MacBook pilot treated Graphiti and FalkorDB as a derived sidecar index.
The MacBook pilot required explicit CLI commands only.
The MacBook pilot did not wire Graphiti recall into Claude or Codex prompt injection.
The MacBook pilot required Graphiti to be rebuildable from Markdown memory files.

## Historical rollback relationships

The MacBook pilot rollback stops or removes only the Graphiti and FalkorDB runtime.
The MacBook pilot rollback must not delete Markdown memory files.
The MacBook pilot rollback must not delete Milvus data.
The MacBook pilot rollback must not delete `.memsearch/memory`.
The historical `.memsearch/graphiti-manifest.json` was a derived Graphiti manifest, not a memory source of truth.

