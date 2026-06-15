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
- Tailscale Funnel is off. Tailscale Serve provides private Tailnet TCP forwarding.

The Tailnet MCP route uses Tailscale Serve raw TCP forwarding on the Mini:

```text
dom-kamet.tailf78a36.ts.net:8018 -> 127.0.0.1:18018
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

- Repo checkout on Mini: `~/Projects/memsearch`.
- Dedicated Colima home: `/Volumes/SSD/graphiti-mon316/colima-home`.
- Preferred logs: `/Volumes/SSD/graphiti-mon316/logs`.
- LaunchAgent fallback logs: `~/Library/Logs/graphiti-mon316`.
- LaunchAgent fallback state: `~/Library/Application Support/graphiti-mon316/state`.
- Secrets: `~/.secrets/graphiti.env`.
- Local MCP client venv: `~/venvs/graphiti-mcp-client`.
- Graphiti LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316.plist`.
- Awake LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-awake.plist`.
- Tailscale Serve config: `tailscale serve --tcp 8018 tcp://127.0.0.1:18018`.
- Retired Tailnet forward LaunchAgent: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-tailnet-proxy.plist`, disabled with `launchctl disable`.

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
~/Projects/memsearch/bin/start-graphiti-mon316.sh
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
~/Projects/memsearch/bin/stop-graphiti-mon316.sh
```

Stop the dedicated Graphiti Colima profile too:

```bash
~/Projects/memsearch/bin/stop-graphiti-mon316.sh --stop-colima
```

## Curated freshness workflow

Graphiti freshness is candidate-first. The weekly candidate job writes a report under `outputs/YYYY-MM-DD/` and does not mutate Graphiti. Approved batches are ingested manually with `graph-index-curated --dry-run` followed by a capped real run.

Only `current` statements with explicit evidence are eligible for human review as seed candidates. Historical, superseded, unsafe, raw transcript, raw Manus export, full `.memsearch/memory`, stale route, and troubleshooting symptom sources stay out of ingest-ready output by default.

## Runtime automation

The Mini automation is user-session supervised. It is not reboot-without-login guaranteed until a separate admin-level power/login plan is approved and tested.

Rendered LaunchAgents:

- `com.monkhouse.graphiti-mon316-watchdog`: runs `bin/graphiti-watchdog-mon316.sh` every 300 seconds and at load.
- `com.monkhouse.graphiti-mon316-backup`: runs `bin/graphiti-backup-mon316.sh` daily at 03:15.
- `com.memsearch.source-freshness-proof`: runs `bin/graphiti-source-freshness-proof-mon316.sh` daily at 06:45.
- `com.memsearch.graphiti-candidate-report`: runs `bin/graphiti-candidate-report-mon316.sh` Monday at 07:00.

The watchdog uses the dedicated `graphiti-mon316` Colima socket when present and only runs the narrow recovery commands returned by `memsearch graph-watchdog`. It refuses commands that mention Milvus, destructive Compose volume removal, or Docker volume deletion.

macOS may deny user LaunchAgents write access to the external SSD even when the same user can write there from an interactive shell. The Graphiti wrappers therefore treat SSD logs, backup, and watchdog state as preferred paths and fall back to the user Library paths above when launchd reports `Operation not permitted`.

## Backup and restore drill

Nightly backups use `memsearch graph-backup --execute --backup-root /Volumes/SSD/graphiti-mon316/backups --retain-days 30 --prune-to-trash`.

The backup sequence is:

1. Run a FalkorDB/Redis snapshot command inside `graphiti-mon316-falkordb-1`.
2. Copy `/var/lib/falkordb/data` from the container into a dated backup directory.
3. Write `metadata.json` with the timestamp, container name, volume name, and data path.
4. After a successful new backup, move old dated backup directories to `~/.Trash/graphiti-mon316-backups/` according to retention.

Restore drills must use a temporary non-production graph group or separate project. Do not clear the production curated group unless the rollback procedure below is being executed.

Evidence to save after a drill:

- backup directory path;
- `metadata.json`;
- restore target group or project;
- `graph-status` output;
- `graph-eval --json-output` output.

## Approved capped ingest runbook

1. Run `uv run memsearch graph-status`.
2. Run `uv run memsearch graph-eval --json-output`.
3. Copy `.memsearch/graphiti-curated-manifest.json` to `.memsearch/manifest-checkpoints/`.
4. Run `uv run memsearch graph-index-curated <approved-seed-file> --dry-run`.
5. Confirm selected, excluded, episode, and pending counts match the approved batch.
6. Run `uv run memsearch graph-index-curated <approved-seed-file> --limit <N>`.
7. Poll `uv run memsearch graph-eval --json-output` until pass or bounded failure.
8. Run practical negative-control searches.
9. Update Linear with source file, manifest count, eval result, and keep/remove decision.

## Rollback

Stop or remove only the Graphiti/FalkorDB runtime. Do not delete Markdown memory files, Milvus data, or `.memsearch/memory`.

The derived Graphiti manifest can be left in `.memsearch/graphiti-manifest.json`; `.memsearch/` is already ignored by git.

The runtime is currently login-session supervised, not reboot-without-login guaranteed. Reboot-proof operation remains blocked until the Mini has an approved admin-level power/login setup.

For curated ingest rollback:

1. Save the failing graph-search or graph-eval output.
2. Clear only `ms_memsearch_active_curated_v1` with the guarded command:

```bash
uv run memsearch graph-clear-group \
  --group-id ms_memsearch_active_curated_v1 \
  --confirm-group-id ms_memsearch_active_curated_v1 \
  --execute
```

3. Restore `.memsearch/graphiti-curated-manifest.json` from the pre-batch checkpoint.
4. Rebuild from known-good seed files only.
5. Re-run `uv run memsearch graph-eval --json-output`.
6. Record the rejected batch and recovery evidence in Linear.

Never run destructive Compose volume-removal commands as a Graphiti rollback shortcut.
