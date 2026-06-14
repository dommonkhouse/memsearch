<!--
MON-316 capped Graphiti relationship seed batch 014 anchor correction.
Reviewed on 2026-06-14.
Source map: docs/graphiti-curated-seeds/capped-batch-014-sources.md
-->

# Graphiti MCP route anchor relationships

The Graphiti MCP route answer must include http://dom-kamet.tailf78a36.ts.net:8018/mcp.
The Graphiti MCP route answer must include Host header 127.0.0.1:18018.
The Graphiti MCP route answer must include DNS-rebinding.
The Graphiti MCP route answer must warn against /mcp/ with a trailing slash.

# Graphiti runtime isolation anchor relationships

The runtime isolation answer must include dedicated Colima profile graphiti-mon316.
The runtime isolation answer must include /Volumes/SSD/graphiti-mon316.
The runtime isolation answer must include FalkorDB and Milvus separation.

# Graphiti login supervision anchor relationships

The supervision answer must include login-session supervised.
The supervision answer must include reboot-without-login.
The supervision answer must include autoLoginUser_missing, kcpassword_missing, and sudo_unavailable.

# Graphiti rollback anchor relationships

The rollback answer must include Stop or remove only the Graphiti/FalkorDB runtime.
The rollback answer must include Do not delete Markdown memory files.
The rollback answer must include Milvus data and .memsearch/memory.
The rollback answer must include derived Graphiti manifest.
