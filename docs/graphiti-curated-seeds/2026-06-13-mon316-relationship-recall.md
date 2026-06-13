<!--
MON-316 curated Graphiti relationship seeds.
Rebuild command: memsearch graph-index-curated docs/graphiti-curated-seeds --limit 2
This does not replace the curated memory dry-run/review gate.
-->

# MON-316 Graphiti Tailscale Serve relationship update

Graphiti and FalkorDB are running as the MemSearch graph sidecar on the Mac Mini `dom-kamet.tailf78a36.ts.net`.
The current client route for Graphiti MCP is `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with Host header `127.0.0.1:18018`.
Tailscale Serve owns port `8018` and forwards raw TCP to `127.0.0.1:18018`.
This replaced the earlier supervised SSH-forward route for the Graphiti tailnet access path.
Graphiti health through the tailnet route returns healthy, and MemSearch `graph-status` reports Graphiti MCP is connected to FalkorDB.
Default `memsearch search` queries Graphiti as a separate graph lane while preserving vector results as primary.

# MON-316 branch relationship update

The active MON-316 workstream is the branch `dom/mon-316-graphiti-falkordb` in `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti`.
Local HEAD `1ea2509` is the commit `feat: add curated graphiti recall path` on that branch.
That commit added the curated Graphiti recall path for MemSearch, including `memsearch graph-index-curated`, default graph-on `memsearch search`, `--no-graph`, and vector-first Graphiti fallback behaviour.
The branch `dom/mon-316-graphiti-falkordb` connects MON-316 to Graphiti.
The branch `dom/mon-316-graphiti-falkordb` connects MON-316 to FalkorDB.
The branch `dom/mon-316-graphiti-falkordb` connects Graphiti relationship recall to the FalkorDB-backed graph sidecar.
Graphiti/FalkorDB remains a sidecar; vector results remain primary.
