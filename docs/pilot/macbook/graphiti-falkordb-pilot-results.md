# Graphiti FalkorDB pilot results

Historical note: these results record the earlier MacBook local pilot preflight.
The current verified runtime results are in `docs/graphiti-falkordb-pilot-results.md`.

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

- Proceed to Graphiti MCP protocol probing.
- Use the active `colima` Docker context.
- Keep the Graphiti checkout outside the MemSearch repo.

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

- Do not proceed to Graphiti MCP protocol probing.
- Do not implement a guessed client route.
- Resume Task 3 only after Docker, Colima, Podman, or an equivalent verified runtime route is available.

Recommendation: change. Install or enable a container runtime, then rerun the Task 3 preflight before continuing runtime-dependent Tasks 4-8.
