<!--
MON-316 capped Graphiti relationship seed batch 014 source map.
Reviewed on 2026-06-14.
-->

# Source files reviewed for capped batch 014

- docs/graphiti-falkordb.md
- docs/graphiti-falkordb-pilot-results.md

# Relationship extraction notes

- Graphiti MCP route relationships came from the current status and MCP probe sections documenting the Tailnet endpoint, Host header, DNS-rebinding protection, and trailing slash warning.
- Graphiti runtime isolation relationships came from current status and runtime verification sections documenting Mac Mini host, SSD path, dedicated Colima profile, local binding, internal FalkorDB, and existing Milvus isolation.
- Graphiti login supervision relationships came from the reboot/login status and rollback sections documenting login-session supervision and missing reboot-proof prerequisites.
- Graphiti rollback relationships came from the rollback section documenting what to stop and what must be preserved.

# Explicit exclusions

- Historical MacBook pilot preflight details were not turned into current-state seeds.
- The superseded `ms_memsearch_ae2d4f9b` example group ID was not used as a current curated group.
- No full .memsearch/memory ingestion was performed.
- Runtime manifest and checkpoint files remain local and are not committed.
