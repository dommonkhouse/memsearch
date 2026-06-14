<!--
MON-316 capped Graphiti relationship seed batch 014.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-014-sources.md
-->

# Graphiti MCP route relationships

Graphiti MCP clients use endpoint http://dom-kamet.tailf78a36.ts.net:8018/mcp.
Graphiti MCP clients use Host header 127.0.0.1:18018.
The Graphiti MCP server has DNS-rebinding protection for localhost hosts.
Tailscale Serve forwards dom-kamet.tailf78a36.ts.net:8018 to 127.0.0.1:18018.
Clients should not use /mcp/ with a trailing slash.
The /mcp/ trailing slash redirects through the Host header and can break remote clients.

# Graphiti runtime isolation relationships

Graphiti and FalkorDB run on the Mac Mini dom-kamet.tailf78a36.ts.net.
The Graphiti runtime storage path is /Volumes/SSD/graphiti-mon316.
Graphiti uses the dedicated Colima profile graphiti-mon316.
Graphiti uses COLIMA_HOME /Volumes/SSD/graphiti-mon316/colima-home.
Graphiti binds locally at 127.0.0.1:18018.
FalkorDB stays internal to the Graphiti Compose network and does not publish port 6379.
Existing Milvus continues on the default Colima profile.

# Graphiti login supervision relationships

The current Graphiti deployment is login-session supervised.
The current Graphiti deployment is not verified as reboot-without-login always-on.
Reboot-proof operation remains blocked until approved admin-level power or login setup exists.
The reboot/login blockers are autoLoginUser_missing, kcpassword_missing, and sudo_unavailable.
The awake LaunchAgent keeps the Mac Mini awake while the GUI session exists.

# Graphiti rollback relationships

Graphiti rollback stops or removes only the Graphiti/FalkorDB runtime.
Graphiti rollback must not delete Markdown memory files.
Graphiti rollback must not delete Milvus data.
Graphiti rollback must not delete .memsearch/memory.
The derived Graphiti manifest can remain because Graphiti is rebuildable from Markdown.
