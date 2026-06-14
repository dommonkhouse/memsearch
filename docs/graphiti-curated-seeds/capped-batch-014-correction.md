<!--
MON-316 capped Graphiti relationship seed batch 014 correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-014-sources.md
-->

# Graphiti MCP route correction relationships

The Graphiti MCP route answer includes http://dom-kamet.tailf78a36.ts.net:8018/mcp, Host header, 127.0.0.1:18018, trailing slash, and DNS-rebinding.
Use endpoint http://dom-kamet.tailf78a36.ts.net:8018/mcp.
Use Host header 127.0.0.1:18018.
Do not use /mcp/ with a trailing slash.
The trailing slash route can break remote clients because of DNS-rebinding protection and Host header redirects.

# Graphiti runtime isolation correction relationships

The Graphiti runtime isolation answer includes Mac Mini, dedicated Colima profile, graphiti-mon316, /Volumes/SSD/graphiti-mon316, FalkorDB, and Milvus.
Graphiti runs on the Mac Mini.
Graphiti uses dedicated Colima profile graphiti-mon316.
Graphiti storage lives under /Volumes/SSD/graphiti-mon316.
FalkorDB stays internal to the Graphiti Compose network.
Existing Milvus continues on the default Colima profile.

# Graphiti login supervision correction relationships

The Graphiti login supervision answer includes login-session supervised, reboot-without-login, autoLoginUser_missing, kcpassword_missing, and sudo_unavailable.
The deployment is login-session supervised.
The deployment is not verified as reboot-without-login always-on.
The reboot-proof blockers are autoLoginUser_missing, kcpassword_missing, and sudo_unavailable.

# Graphiti rollback correction relationships

The Graphiti rollback answer includes Stop or remove only the Graphiti/FalkorDB runtime, Do not delete Markdown memory files, Milvus data, .memsearch/memory, and derived Graphiti manifest.
Rollback stops only the Graphiti/FalkorDB runtime.
Rollback preserves Markdown memory files.
Rollback preserves Milvus data.
Rollback preserves .memsearch/memory.
The derived Graphiti manifest can remain because the graph is rebuildable.
