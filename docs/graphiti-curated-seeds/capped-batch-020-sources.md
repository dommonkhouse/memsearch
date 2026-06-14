# Capped batch 020 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti MacBook pilot-history tuning.

## Reviewed source files

- `docs/pilot/macbook/graphiti-falkordb.md`: safe to distil, unsafe for direct ingestion. It is explicitly historical and contains obsolete local endpoint, group, and manifest examples that must not override the current Mac Mini route.
- `docs/pilot/macbook/graphiti-falkordb-pilot-results.md`: safe to distil, unsafe for direct ingestion. It is explicitly historical and contains preflight outputs, including an earlier blocked state and a later passed local runtime check.

## Evidence statements

- Statement: The MacBook pilot guide is historical, and the current verified runtime route is the Mac Mini/Tailscale Serve route in `docs/graphiti-falkordb.md`.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:3-5`.
- Statement: The MacBook pilot preflight passed on 2026-06-11 at 21:08:49 BST on `Dominic's Macbook`.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:11-21`; `docs/pilot/macbook/graphiti-falkordb-pilot-results.md:5-37`.
- Statement: The MacBook pilot used Docker, Docker Compose, Colima, an active default `colima` context, and available `OPENAI_API_KEY`.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:11-19`; `docs/pilot/macbook/graphiti-falkordb-pilot-results.md:8-37`.
- Statement: The MacBook pilot planned Graphiti MCP on `127.0.0.1:8018`, endpoint `http://127.0.0.1:8018/mcp/`, group `ms_memsearch_ae2d4f9b`, and manifest `.memsearch/graphiti-manifest.json`.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:39-70`.
- Statement: The MacBook pilot kept Markdown as source of truth, Milvus as primary automatic recall, Graphiti/FalkorDB as derived sidecar, explicit CLI only, and graph rebuildable from Markdown.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:25-31`.
- Statement: The 2026-06-11 11:21:43 BST MacBook preflight was blocked because no local container/runtime route was found, and it should not proceed or guess a client route.
  Evidence: `docs/pilot/macbook/graphiti-falkordb-pilot-results.md:54-124`.
- Statement: The MacBook pilot rollback stops only Graphiti/FalkorDB runtime and does not delete Markdown memory files, Milvus data, or `.memsearch/memory`.
  Evidence: `docs/pilot/macbook/graphiti-falkordb.md:75-80`.

