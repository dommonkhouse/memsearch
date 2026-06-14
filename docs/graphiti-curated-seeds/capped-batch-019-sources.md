# Capped batch 019 source review

Reviewed on 2026-06-14 for MON-316 capped Graphiti Mac Mini operations tuning.

## Reviewed source files

- `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md`: safe to distil, unsafe for direct ingestion. It contains durable runtime, routing, launch supervision, probe, and rollback relationships mixed with historical command steps and implementation checklists.

## Evidence statements

- Statement: Graphiti and FalkorDB run as a Mac Mini sidecar, keep Markdown canonical, keep Milvus primary, and use a dedicated Colima profile on `/Volumes/SSD`.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:5-8`.
- Statement: The Mac Mini runtime uses `dom-kamet.tailf78a36.ts.net`, Tailscale, Colima, Graphiti MCP, FalkorDB, LaunchAgent, and `caffeinate`.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:9`.
- Statement: The external SSD was selected because the internal disk had limited free space, `/Volumes/SSD` had about `908 GiB` free, and `/Volumes/Mac Storage` was not writable.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:23-25`.
- Statement: Graphiti runtime state lives under `/Volumes/SSD/graphiti-mon316`, with dedicated Colima profile `graphiti-mon316`, while default Colima remains selected for Milvus.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:53-55`.
- Statement: Tailnet Graphiti access uses Tailscale Serve raw TCP forwarding from `dom-kamet.tailf78a36.ts.net:8018` to `127.0.0.1:18018`, with Funnel off and the old SSH-forward LaunchAgent disabled.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:55-58`.
- Statement: MCP clients must use `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018` because of the DNS-rebinding guard.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:58`.
- Statement: Probe group `ms_memsearch_probe_1781275707` was added, searched, cleared, and verified empty, and Milvus stayed healthy.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:59-60`.
- Statement: Graphiti is not reboot-without-login safe because auto-login, `/etc/kcpassword`, and non-interactive sudo are unavailable.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:42-47`; `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:61`.
- Statement: Graphiti deployment files must avoid exposing FalkorDB remotely, use local-only Graphiti binding, absolute secret env file path, and non-secret examples only.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:65-80`; `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:232-242`.
- Statement: The Graphiti start script must use SSD-backed `COLIMA_HOME`, dedicated Docker socket discovery, and reject the default Milvus Colima socket.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:246-254`.
- Statement: The Graphiti stop script must not delete volumes and must not stop or touch default Colima or Milvus.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:256-260`.
- Statement: User LaunchAgent supervision uses an awake agent with `/usr/bin/caffeinate -ims`, and the Graphiti LaunchAgent uses `RunAtLoad` plus `StartInterval=60`.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:323-351`.
- Statement: Tailscale Serve exposes `http://dom-kamet.tailf78a36.ts.net:8018/health` and `http://dom-kamet.tailf78a36.ts.net:8018/mcp`, with MCP discovery requiring `Host: 127.0.0.1:18018`.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:388-408`; `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:438-443`.
- Statement: Probe work must use temporary groups and cleanup only those probe groups.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:445-461`.
- Statement: Rollback must boot out only Graphiti user agents, stop only Graphiti Compose, avoid `down -v`, preserve named volumes, leave Milvus/default Colima alone, and not delete `/Volumes/SSD/graphiti-mon316` without explicit approval.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:501-524`.
- Statement: Tailscale exposure mistakes are mitigated by binding Docker to localhost, using Tailscale Serve raw TCP forwarding, and keeping Funnel off.
  Evidence: `docs/superpowers/plans/2026-06-12-graphiti-mac-mini-ssd-deployment.md:528-533`.

