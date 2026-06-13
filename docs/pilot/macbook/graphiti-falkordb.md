# Graphiti FalkorDB pilot

Historical note: this file records the earlier MacBook local pilot preflight.
The current verified runtime route is the Mac Mini/Tailscale Serve route in
`docs/graphiti-falkordb.md`.

This guide records the intended local pilot route for adding Graphiti and FalkorDB as an optional MemSearch graph recall layer.

## Current status

Runtime preflight on 2026-06-11 21:08:49 BST passed on `Dominic's Macbook`:

- `docker` is available on `PATH` at `/opt/homebrew/bin/docker`.
- Docker CLI version is `29.5.3`.
- Docker server version is `29.5.2` through the active `colima` context.
- Docker Compose version is `5.1.4`.
- `colima` is available on `PATH` at `/opt/homebrew/bin/colima`.
- Colima is running with Docker runtime on macOS Virtualization.Framework.
- `OPENAI_API_KEY` was available through local secrets.
- Ports `8018` and `6379` were free.

Graphiti/FalkorDB has not been started yet. Runtime-dependent protocol probing can continue from this state.

## Architecture

- Markdown remains the source of truth.
- Milvus remains the primary automatic recall index.
- Graphiti/FalkorDB is a derived sidecar index.
- The pilot must use explicit CLI commands only. Do not wire graph recall into Claude or Codex prompt injection in this version.
- The graph must be rebuildable from Markdown memory files.

## Planned runtime route

When a container runtime is available:

1. Clone Graphiti outside the MemSearch repo:

```bash
cd /Users/dominicmonkhouse/Projects
test -d graphiti/.git || git clone https://github.com/getzep/graphiti.git graphiti
git -C graphiti fetch --all --prune
git -C graphiti status --short --branch
```

2. Use Graphiti's documented MCP server Docker Compose route with FalkorDB.

3. Configure Graphiti MCP to listen on `127.0.0.1:8018`, not the default `8000`, because port `8000` was occupied during planning.

4. Keep secrets in ignored local `.env` files or `~/.secrets/mcp.env`. Do not commit keys.

5. Record the exact Graphiti commit or tag and FalkorDB image before running the live smoke test.

## MemSearch config

Example local configuration:

```toml
[graphiti]
enabled = true
transport = "mcp-streamable-http"
endpoint = "http://127.0.0.1:8018/mcp/"
group_id = "ms_memsearch_ae2d4f9b"
batch_size = 10
request_timeout_seconds = 120
manifest_path = ".memsearch/graphiti-manifest.json"
```

## Planned commands

```bash
memsearch graph-status --endpoint http://127.0.0.1:8018/mcp/
memsearch graph-index <memory-dir> --limit 10 --group-id ms_memsearch_ae2d4f9b
memsearch graph-search "what changed about Kuzu" --group-id ms_memsearch_ae2d4f9b --top-k 5
```

## Rollback

Stop or remove only the Graphiti/FalkorDB runtime. Do not delete Markdown memory files, Milvus data, or `.memsearch/memory`.

The derived Graphiti manifest can be left in `.memsearch/graphiti-manifest.json`; `.memsearch/` is already ignored by git.
