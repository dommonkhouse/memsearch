# Batch 001 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti ingest expansion.

## Source safety decisions

- `docs/graphiti-falkordb.md`: safe to distil, unsafe for direct ingestion. Current runtime facts are in lines 7-39, but later example config still contains older group and manifest names.
- `docs/graphiti-falkordb-pilot-results.md`: safe to distil, unsafe for direct ingestion. The Mac Mini deployment evidence is current in lines 3-175, while later MacBook preflight sections are historical.
- `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md`: safe current seed. Avoid duplicating every existing statement.
- `docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md`: safe current seed. It already labels NordVPN, Meshnet, `.nord`, and `100.87.225.99` as not current or stale.
- `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/tailscale-migration.md`: distil only. Lines 4, 13-18, 25, and 55-56 contain current facts, but lines 21-66 include historical troubleshooting, recovery, `.nord`, Meshnet, and `100.87.225.99`.
- `/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/open-brain-runs-on-the-mini.md`: distil only. Lines 8-21 and 31 contain current Open Brain host facts, while line 23 is historical MacBook/local Postgres context.
- `/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/localhost-for-self-hosted-services.md`: distil only. Lines 7-11 contain the current localhost rule; line 15 is historical incident context.

## Statement evidence

- Statement: Graphiti and FalkorDB run as the MemSearch graph sidecar on the Mac Mini `dom-kamet.tailf78a36.ts.net`.
  Evidence: `docs/graphiti-falkordb.md:7`; `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md:9`.
- Statement: The Graphiti runtime host is the Mac Mini with Tailscale IP `100.72.169.59`.
  Evidence: `docs/graphiti-falkordb.md:9`; `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/tailscale-migration.md:13`.
- Statement: Graphiti uses the dedicated Colima profile `graphiti-mon316`.
  Evidence: `docs/graphiti-falkordb.md:11`; `docs/graphiti-falkordb-pilot-results.md:24-34`.
- Statement: Graphiti stores runtime state under `/Volumes/SSD/graphiti-mon316`.
  Evidence: `docs/graphiti-falkordb.md:10`; `docs/graphiti-falkordb.md:45-46`.
- Statement: Graphiti MCP binds locally at `127.0.0.1:18018`.
  Evidence: `docs/graphiti-falkordb.md:12`; `docs/graphiti-falkordb-pilot-results.md:36-41`.
- Statement: FalkorDB stays internal to the Graphiti Compose network and does not publish port `6379`.
  Evidence: `docs/graphiti-falkordb.md:14`; `docs/graphiti-falkordb-pilot-results.md:36-41`.
- Statement: Tailscale Serve is part of the Mac Mini Graphiti and FalkorDB access path.
  Evidence: `docs/graphiti-falkordb.md:16-28`; `docs/graphiti-falkordb-pilot-results.md:7-13`; `docs/graphiti-falkordb-pilot-results.md:58-68`; `docs/graphiti-falkordb-pilot-results.md:105-112`.
- Statement: Milvus remains the primary automatic recall index.
  Evidence: `docs/graphiti-falkordb.md:35-37`; `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md:24`.
- Statement: Graphiti and FalkorDB remain a derived sidecar index.
  Evidence: `docs/graphiti-falkordb.md:35-39`; `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md:24`.
- Statement: Tailscale Serve forwards `dom-kamet.tailf78a36.ts.net:8018` to `127.0.0.1:18018`.
  Evidence: `docs/graphiti-falkordb.md:18-22`; `docs/graphiti-falkordb-pilot-results.md:7-13`; `docs/graphiti-falkordb-pilot-results.md:58-68`.
- Statement: Tailscale Funnel is off for the Graphiti route.
  Evidence: `docs/graphiti-falkordb.md:16`; `docs/graphiti-falkordb-pilot-results.md:13`.
- Statement: Graphiti MCP clients use endpoint `http://dom-kamet.tailf78a36.ts.net:8018/mcp`.
  Evidence: `docs/graphiti-falkordb.md:24-31`; `docs/graphiti-falkordb-pilot-results.md:105-112`.
- Statement: Graphiti MCP clients use Host header `127.0.0.1:18018`.
  Evidence: `docs/graphiti-falkordb.md:24-31`; `docs/graphiti-falkordb-pilot-results.md:105-112`.
- Statement: The retired Graphiti tailnet proxy LaunchAgent is disabled.
  Evidence: `docs/graphiti-falkordb.md:51-52`; `docs/graphiti-falkordb-pilot-results.md:50-56`.
- Statement: Tailscale Serve owns the current Graphiti tailnet route.
  Evidence: `docs/graphiti-falkordb.md:16-22`; `docs/graphiti-curated-seeds/2026-06-13-mon316-relationship-recall.md:11-12`.
- Statement: Open Brain production runs on the Mac Mini.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/open-brain-runs-on-the-mini.md:17-21`.
- Statement: Remote Open Brain access uses `http://dom-kamet.tailf78a36.ts.net:8787`.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/open-brain-runs-on-the-mini.md:31`.
- Statement: Local-on-Mac-Mini Open Brain access uses `localhost` or `127.0.0.1`.
  Evidence: `/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/localhost-for-self-hosted-services.md:7-11`; `docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md:18`.
- Statement: Open Brain should not use `.nord` hostnames.
  Evidence: `docs/graphiti-curated-seeds/2026-06-13-tailscale-current-state.md:19-24`; `/Users/dominicmonkhouse/Projects/claude-config/memory/projects/tailscale-migration.md:25`.
