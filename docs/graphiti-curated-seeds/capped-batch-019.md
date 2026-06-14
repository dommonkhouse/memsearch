# Capped batch 019: Mac Mini Graphiti operations

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

This batch distils durable relationships from the Mac Mini Graphiti SSD deployment plan.
It does not ingest `.memsearch/memory` or raw task transcripts.

## Mac Mini runtime isolation relationships

Graphiti and FalkorDB run as a separate MemSearch graph sidecar on the Mac Mini `dom-kamet.tailf78a36.ts.net`.
Graphiti runtime state lives under `/Volumes/SSD/graphiti-mon316`.
Graphiti uses the dedicated Colima profile `graphiti-mon316`.
Graphiti sets `COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home`.
Milvus remains on the default Colima profile and must not be stopped or moved as part of Graphiti operations.
Markdown remains the canonical memory source.
Milvus remains the primary automatic recall layer.
Graphiti and FalkorDB are a derived sidecar index.

## Tailnet MCP routing relationships

Graphiti is bound locally as `127.0.0.1:18018->8000`.
Tailscale Serve raw TCP forwarding exposes Graphiti privately at `dom-kamet.tailf78a36.ts.net:8018`.
Graphiti health is reached at `http://dom-kamet.tailf78a36.ts.net:8018/health`.
Graphiti MCP is reached at `http://dom-kamet.tailf78a36.ts.net:8018/mcp`.
Graphiti MCP clients must send `Host: 127.0.0.1:18018`.
The Host header is required because the Graphiti MCP server has localhost DNS-rebinding protection.
Graphiti MCP clients must not use `/mcp/` with a trailing slash.
The retired `com.monkhouse.graphiti-mon316-tailnet-proxy` SSH-forward LaunchAgent is disabled.
Tailscale Funnel remains off.

## Login-session supervision relationships

Graphiti uses user LaunchAgent `com.monkhouse.graphiti-mon316` for idempotent runtime reconciliation.
The Graphiti LaunchAgent uses `RunAtLoad` plus `StartInterval=60`.
The Graphiti LaunchAgent does not use a foreground `KeepAlive` wrapper around `docker compose up -d`.
The awake LaunchAgent is `com.monkhouse.graphiti-mon316-awake`.
The awake LaunchAgent runs `/usr/bin/caffeinate -ims`.
Graphiti is login-session always-on while the user session exists.
Graphiti is not verified as reboot-without-login always-on.
Reboot-without-login remains blocked by missing `autoLoginUser`, missing `/etc/kcpassword`, and unavailable non-interactive sudo.

## Probe and rollback safety relationships

Graphiti probe episodes must use a temporary group such as `ms_memsearch_probe_<timestamp>`.
Probe cleanup must clear only the temporary probe group.
Probe cleanup must not clear non-probe graph data.
Graphiti rollback stops only Graphiti user agents and the Graphiti Compose runtime.
Graphiti rollback must not use `docker compose down -v`.
Graphiti rollback must not remove named volumes without explicit approval.
Graphiti rollback must not stop or delete default Colima or Milvus.
Graphiti rollback must not delete `/Volumes/SSD/graphiti-mon316` without explicit approval.
Graphiti rollback must preserve Markdown memory files, Milvus data, `.memsearch/memory`, and the Graphiti manifest unless an explicit reviewed cleanup says otherwise.

