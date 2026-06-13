<!--
MON-316 capped Graphiti relationship seed batch 001.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-001-sources.md
-->

# Graphiti Mac Mini runtime relationships

Graphiti and FalkorDB run as the MemSearch graph sidecar on the Mac Mini `dom-kamet.tailf78a36.ts.net`.
The Graphiti runtime host is the Mac Mini with Tailscale IP `100.72.169.59`.
Graphiti uses the dedicated Colima profile `graphiti-mon316`.
Graphiti stores runtime state under `/Volumes/SSD/graphiti-mon316`.
Graphiti MCP binds locally at `127.0.0.1:18018`.
FalkorDB stays internal to the Graphiti Compose network and does not publish port `6379`.
Tailscale Serve is part of the Mac Mini Graphiti and FalkorDB access path.
Milvus remains the primary automatic recall index.
Graphiti and FalkorDB remain a derived sidecar index.

# Graphiti Tailnet route relationships

Tailscale Serve forwards `dom-kamet.tailf78a36.ts.net:8018` to `127.0.0.1:18018`.
Tailscale Funnel is off for the Graphiti route.
Graphiti MCP clients use endpoint `http://dom-kamet.tailf78a36.ts.net:8018/mcp`.
Graphiti MCP clients use Host header `127.0.0.1:18018`.
The retired Graphiti tailnet proxy LaunchAgent is disabled.
Tailscale Serve owns the current Graphiti tailnet route.

# Open Brain Mac Mini route relationships

Open Brain production runs on the Mac Mini.
Remote Open Brain access uses `http://dom-kamet.tailf78a36.ts.net:8787`.
Local-on-Mac-Mini Open Brain access uses `localhost` or `127.0.0.1`.
Open Brain should not use `.nord` hostnames.
