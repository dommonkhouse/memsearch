# Graphiti FalkorDB pilot

This guide records the verified Mac Mini route for adding Graphiti and FalkorDB as an optional MemSearch graph recall layer.

## Current status

Graphiti/FalkorDB is running on the Mac Mini `dom-kamet.tailf78a36.ts.net` as of 2026-06-12.

- Runtime host: Mac Mini, Tailscale IP `100.72.169.59`.
- Runtime storage: `/Volumes/SSD/graphiti-mon316`.
- Container runtime: dedicated Colima profile `graphiti-mon316`, with `COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home`.
- Graphiti container binding: `127.0.0.1:18018->8000`.
- Tailnet endpoint: `http://dom-kamet.tailf78a36.ts.net:8018/health`.
- FalkorDB is internal to the Graphiti Compose network and does not publish `6379`.
- Existing Milvus continues to run on the default Colima profile.
- Tailscale Funnel is off. Tailscale Serve is not enabled on the Tailnet.

The Tailnet MCP route uses a supervised SSH local forward on the Mini:

```text
100.72.169.59:8018 -> 127.0.0.1:18018
```

The Graphiti MCP server has DNS-rebinding protection enabled for localhost hosts. MCP clients connecting through the Tailnet route must use:

```text
URL:    http://dom-kamet.tailf78a36.ts.net:8018/mcp
Header: Host: 127.0.0.1:18018
```

Do not use `/mcp/` with a trailing slash. The server redirects `/mcp/` to `/mcp` using the Host header, which can break remote clients.

## Architecture

- Markdown remains the source of truth.
- Milvus remains the primary automatic recall index.
- Graphiti/FalkorDB is a derived sidecar index.
- The Graphiti runtime is isolated from Milvus by a dedicated Colima profile and Docker socket.
- The pilot uses explicit MCP calls only. Do not wire graph recall into Claude or Codex prompt injection in this version.
- The graph must be rebuildable from Markdown memory files.

## Runtime files

- Repo checkout on Mini: `~/Projects/memsearch-mon316-graphiti-mini`.
- Dedicated Colima home: `/Volumes/SSD/graphiti-mon316/colima-home`.
- Logs: `/Volumes/SSD/graphiti-mon316/logs`.
- Secrets: `~/.secrets/graphiti.env`.
- Local MCP client venv: `~/venvs/graphiti-mcp-client`.
- Graphiti LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316.plist`.
- Awake LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-awake.plist`.
- Tailnet forward LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-tailnet-proxy.plist`.

## MemSearch config

Example local configuration:

```toml
[graphiti]
enabled = true
transport = "mcp-streamable-http"
endpoint = "http://dom-kamet.tailf78a36.ts.net:8018/mcp"
host_header = "127.0.0.1:18018"
group_id = "ms_memsearch_ae2d4f9b"
batch_size = 10
request_timeout_seconds = 120
manifest_path = ".memsearch/graphiti-manifest.json"
```

## Planned commands

```bash
memsearch graph-status --endpoint http://dom-kamet.tailf78a36.ts.net:8018/mcp --host-header 127.0.0.1:18018
memsearch graph-index <memory-dir> --limit 10 --group-id ms_memsearch_ae2d4f9b
memsearch graph-search "what changed about Kuzu" --group-id ms_memsearch_ae2d4f9b --top-k 5
```

## Operations

Start or reconcile Graphiti on the Mini:

```bash
~/Projects/memsearch-mon316-graphiti-mini/bin/start-graphiti-mon316.sh
```

Verify the MCP client from the Mini:

```bash
~/venvs/graphiti-mcp-client/bin/python - <<'PY'
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:18018/mcp") as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(",".join(sorted(tool.name for tool in tools.tools)))

asyncio.run(main())
PY
```

Stop only Graphiti containers, leaving volumes and Milvus untouched:

```bash
~/Projects/memsearch-mon316-graphiti-mini/bin/stop-graphiti-mon316.sh
```

Stop the dedicated Graphiti Colima profile too:

```bash
~/Projects/memsearch-mon316-graphiti-mini/bin/stop-graphiti-mon316.sh --stop-colima
```

## Rollback

Stop or remove only the Graphiti/FalkorDB runtime. Do not delete Markdown memory files, Milvus data, or `.memsearch/memory`.

The derived Graphiti manifest can be left in `.memsearch/graphiti-manifest.json`; `.memsearch/` is already ignored by git.

The runtime is currently login-session supervised, not reboot-without-login guaranteed. Reboot-proof operation remains blocked until the Mini has an approved admin-level power/login setup.
