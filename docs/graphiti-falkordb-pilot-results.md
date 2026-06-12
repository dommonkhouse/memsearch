# Graphiti FalkorDB pilot results

## 2026-06-12 Mac Mini SSD deployment

Status: passed.

The private Tailnet route uses Tailscale Serve raw TCP forwarding:

```text
dom-kamet.tailf78a36.ts.net:8018 -> 127.0.0.1:18018
```

Tailscale Funnel remains off.

### Runtime verification

Mac Mini identity:

```text
100.72.169.59
mini_confirmed
```

Dedicated Colima profile:

```text
Profile: graphiti-mon316
COLIMA_HOME: /Volumes/SSD/graphiti-mon316/colima-home
CPU: 2
Memory: 4 GiB
Disk: 20 GiB
Runtime: docker
Socket: /Volumes/SSD/graphiti-mon316/colima-home/graphiti-mon316/docker.sock
```

Graphiti Compose state:

```text
graphiti-mon316-falkordb-1       Up 2 hours (healthy)   6379/tcp
graphiti-mon316-graphiti-mcp-1   Up 2 hours (healthy)   127.0.0.1:18018->8000/tcp
```

Health checks:

```text
Mini Tailnet IP: {"status":"healthy","service":"graphiti-mcp"}
MacBook Tailnet DNS: {"status":"healthy","service":"graphiti-mcp"}
```

LaunchAgents:

```text
com.monkhouse.graphiti-mon316                 state = not running, last exit code = 0
com.monkhouse.graphiti-mon316-tailnet-proxy   disabled, retired after Tailscale Serve TCP route was verified
com.monkhouse.graphiti-mon316-awake           state = running
```

Tailscale Serve:

```json
{
  "TCP": {
    "8018": {
      "TCPForward": "127.0.0.1:18018"
    }
  }
}
```

Awake assertions:

```text
PreventDiskIdle                1
PreventSystemSleep             1
PreventUserIdleSystemSleep     1
pid 8320(caffeinate): asserting forever
```

Milvus after deployment:

```text
milvus-etcd         Up 20 hours (healthy)
milvus-minio        Up 20 hours (healthy)
milvus-standalone   Up 9 minutes (healthy)
Milvus health: OK
Docker context after checks: colima
```

Disk:

```text
/Volumes/SSD             931Gi   64Gi   868Gi   7%
/System/Volumes/Data     228Gi  180Gi    11Gi  95%
```

Graphiti Docker storage:

```text
falkordb/falkordb:latest                 609 MB
zepai/knowledge-graph-mcp:standalone     581 MB
graphiti_mon316_falkordb_data            9.615 kB after probe cleanup
graphiti_mon316_mcp_logs                 0 B
```

### MCP probe

MCP endpoint used:

```text
URL: http://dom-kamet.tailf78a36.ts.net:8018/mcp
Header: Host: 127.0.0.1:18018
```

Tool discovery:

```text
add_memory
clear_graph
delete_entity_edge
delete_episode
get_entity_edge
get_episodes
get_status
search_memory_facts
search_nodes
```

Mini-local MCP client:

```text
venv: ~/venvs/graphiti-mcp-client
package: mcp>=1.27.2,<2
endpoint verified from Mini: http://127.0.0.1:18018/mcp
result: MCP_CLIENT_OK
```

Status:

```json
{
  "status": "ok",
  "message": "Graphiti MCP server is running and connected to falkordb database"
}
```

Probe group:

```text
group_id: ms_memsearch_probe_1781275707
token: graphiti-tailnet-probe-1781275707
episode_uuid: 38527677-13c8-4f97-b912-d18cb52438d4
```

Probe results:

```text
add_memory queued the episode.
get_episodes found the episode on polling attempt 6.
search_memory_facts returned fact 27f24431-ccd0-4e57-ae60-2ac8e5a129f4.
search_nodes returned five nodes.
clear_graph cleared only group ms_memsearch_probe_1781275707.
get_episodes after cleanup returned no episodes.
```

### Reboot/login status

The Mini is not yet verified as reboot-without-login always-on:

```text
autoLoginUser_missing
kcpassword_missing
sudo_unavailable
```

Current deployment is login-session supervised. It should remain up while the `dominicmonkhouse` GUI session exists and the awake LaunchAgent is loaded.

## 2026-06-11 21:08:49 BST preflight

Status: passed.

Runtime route: Colima plus Docker CLI/Compose on `Dominic's Macbook`.

Commands run:

```bash
command -v docker || true
docker --version 2>/dev/null || true
docker compose version 2>/dev/null || true
command -v colima || true
colima status 2>&1
docker info --format 'Server={{.ServerVersion}} Context={{.Name}} Driver={{.Driver}}'
```

Output:

```text
docker=/opt/homebrew/bin/docker
Docker version 29.5.3, build d1c06ef6b4
Docker Compose version 5.1.4
colima=/opt/homebrew/bin/colima
colima is running using macOS Virtualization.Framework
arch: aarch64
runtime: docker
mountType: virtiofs
docker socket: unix:///Users/dominicmonkhouse/.colima/default/docker.sock
containerd socket: unix:///Users/dominicmonkhouse/.colima/default/containerd.sock
Server=29.5.2 Context=colima Driver=overlayfs
```

Credential check:

```bash
set -a
[ -f "$HOME/.secrets/mcp.env" ] && source "$HOME/.secrets/mcp.env"
set +a
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY available" || echo "OPENAI_API_KEY missing"
```

Output:

```text
OPENAI_API_KEY available
OPENAI_BASE_URL unset
```

Port check:

```bash
lsof -nP -iTCP:8018 -sTCP:LISTEN || true
lsof -nP -iTCP:6379 -sTCP:LISTEN || true
```

Output:

```text
```

Decision:

- Superseded by the Mac Mini SSD deployment above.
- Preserve this as MacBook pilot evidence only.

## 2026-06-11 11:21:43 BST preflight

Status: blocked.

Reason: no local container/runtime route found.

Commands run:

```bash
command -v docker || true
docker --version 2>/dev/null || true
command -v colima || true
command -v podman || true
```

Output:

```text
```

Credential check:

```bash
set -a
[ -f "$HOME/.secrets/mcp.env" ] && source "$HOME/.secrets/mcp.env"
set +a
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY available" || echo "OPENAI_API_KEY missing"
```

Output:

```text
OPENAI_API_KEY available
```

Port check:

```bash
lsof -nP -iTCP:8018 -sTCP:LISTEN || true
lsof -nP -iTCP:6379 -sTCP:LISTEN || true
```

Output:

```text
```

Decision:

- Superseded by later runtime availability and Mac Mini deployment.
