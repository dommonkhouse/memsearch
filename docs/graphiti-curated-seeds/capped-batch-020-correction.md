# Capped batch 020 correction: historical MacBook route anchors

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

The MacBook Graphiti pilot route is historical.
The MacBook Graphiti pilot route is not the current route.
The historical MacBook Graphiti route used `http://127.0.0.1:8018/mcp/`.
The historical MacBook Graphiti route used group `ms_memsearch_ae2d4f9b`.
The historical MacBook Graphiti route used manifest `.memsearch/graphiti-manifest.json`.
The current Graphiti route is the Mac Mini Tailscale Serve route.
The current Graphiti route uses `http://dom-kamet.tailf78a36.ts.net:8018/mcp`.
The current Graphiti route uses `Host: 127.0.0.1:18018`.
The current Graphiti curated group is `ms_memsearch_active_curated_v1`.
The current Graphiti curated manifest is `.memsearch/graphiti-curated-manifest.json`.

The 2026-06-11 11:21:43 BST MacBook Graphiti preflight was blocked.
The blocked MacBook Graphiti preflight found no local container/runtime route.
The blocked MacBook Graphiti preflight must not proceed to Graphiti MCP protocol probing.
The blocked MacBook Graphiti preflight must not implement a guessed client route.

