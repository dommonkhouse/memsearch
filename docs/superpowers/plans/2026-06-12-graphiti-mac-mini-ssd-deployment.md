# Graphiti Mac Mini SSD Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Graphiti + FalkorDB as an always-on MemSearch graph sidecar on the Mac Mini, using the external SSD for Graphiti runtime state and leaving the existing Milvus service untouched.

**Architecture:** Keep Markdown as canonical memory and Milvus as the primary semantic recall layer. Run Graphiti/FalkorDB as a separate Mac Mini sidecar with a dedicated Colima profile whose `COLIMA_HOME` lives on `/Volumes/SSD`, and expose Graphiti through a local-only container binding plus a supervised Tailnet SSH forward. Use user LaunchAgents for login-session supervision, and treat reboot-without-login survivability as blocked until the Mini has an approved admin-level power/login fix.

**Tech Stack:** macOS Mac Mini `dom-kamet.tailf78a36.ts.net`, Tailscale, Colima, Docker CLI/Compose, Graphiti MCP server, FalkorDB, LaunchAgent, `caffeinate`, shell scripts, MemSearch docs.

---

## Evidence Checked

- Existing Linear issue: `MON-316` tracks the broader Graphiti/FalkorDB memory-layer work.
- Existing broader plan: `/Users/dominicmonkhouse/Projects/memsearch/docs/superpowers/plans/2026-06-11-graphiti-falkordb-memory-layer.md`.
- Active branch: `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti` on `dom/mon-316-graphiti-falkordb`.
- MacBook state: Colima stopped; ports `8018` and `6379` clear.
- Mac Mini identity: `dom-kamet.tailf78a36.ts.net`; Tailscale running; no Tailscale Serve or Funnel config currently set.
- Mac Mini Docker state: default Colima profile running `4 CPU / 8 GiB / 30 GiB`; existing `milvus-standalone` Compose project running.
- Milvus persisted data size: `637 MB` under `~/Projects/milvus-standalone/volumes`.
- Memory corpus size: `1.4 MB` Markdown across roughly `322` files.
- Mac Mini internal disk: `33 GiB` free, so avoid creating a large Graphiti VM on the internal disk.
- External `/Volumes/SSD`: writable, HFS, about `908 GiB` free, suitable as the Graphiti runtime location after a Colima smoke test.
- `/Volumes/Mac Storage`: not writable to the user and appears tied to Time Machine/APFS storage. Do not use it for Graphiti.
- Colima upstream docs confirm `$COLIMA_HOME` overrides the base directory and profiles are independent instances.
- Colima docs warn external paths outside `/Users/$USER` need explicit mount configuration if containers need bind mounts from them.
- FalkorDB docs provide `GRAPH.MEMORY` for measuring graph memory after ingest; there is no reliable published Graphiti "MB markdown to GB graph" sizing benchmark.

## Current State

- The original MacBook pilot evidence has been preserved under:
  - `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti/docs/pilot/macbook/graphiti-falkordb.md`
  - `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti/docs/pilot/macbook/graphiti-falkordb-pilot-results.md`
  - `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti/docs/pilot/macbook/test_graphiti_client.py`
- The active repo is dirty before this plan:
  - Modified: `docs/graphiti-falkordb.md`
  - Modified: `docs/graphiti-falkordb-pilot-results.md`
  - Untracked: `docs/pilot/`
  - Untracked: `tests/test_graphiti_client.py`
- Do not revert, delete, or overwrite those changes. Work with them.
- The Mini cannot yet be called reboot-proof:
  - `autoLoginUser` is missing.
  - `/etc/kcpassword` is missing.
  - `pmset sleep` is `1`.
  - `sudo -n true` is unavailable over SSH.
  - A GUI user session exists for `dominicmonkhouse`, so user LaunchAgents can run while that session exists.

## Execution Result

Status on 2026-06-12: completed.

- Graphiti/FalkorDB is running on the Mini with runtime state under `/Volumes/SSD/graphiti-mon316`.
- The dedicated Colima profile is `graphiti-mon316`; the default `colima` context remains selected for Milvus.
- Graphiti MCP is bound inside Docker as `127.0.0.1:18018->8000`.
- Tailnet access is provided by `com.monkhouse.graphiti-mon316-tailnet-proxy`, an SSH forward from `100.72.169.59:8018` to `127.0.0.1:18018`.
- Tailscale Serve could not be used because Serve is not enabled on the Tailnet. Funnel remains off.
- MCP clients should use `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018` to satisfy the Graphiti MCP server's localhost DNS-rebinding guard.
- Probe group `ms_memsearch_probe_1781275707` was added, searched, and cleared. Cleanup verification returned no episodes.
- Existing Milvus containers remained healthy after deployment.
- Reboot-without-login remains blocked by missing auto-login, missing `/etc/kcpassword`, and unavailable non-interactive sudo.

## Files and Responsibilities

- Create: `deploy/graphiti/docker-compose.yml`
  - Base Graphiti + FalkorDB Compose definition with local-only host port bindings.
- Create: `deploy/graphiti/docker-compose.mini.yml`
  - Mini-specific overrides: localhost Graphiti binding on `127.0.0.1:18018:8000`, no remote FalkorDB exposure, named volumes.
- Create: `deploy/graphiti/env.example`
  - Non-secret example keys only. No real secrets.
- Create: `bin/start-graphiti-mon316.sh`
  - Starts the SSD-backed Colima profile and then starts the Graphiti Compose project.
- Create: `bin/stop-graphiti-mon316.sh`
  - Stops Graphiti Compose and optionally stops only the dedicated Graphiti Colima profile. Must not touch Milvus/default Colima.
- Create on Mini, not committed: `/Volumes/SSD/graphiti-mon316/colima-home/`
  - Dedicated `COLIMA_HOME` for the `graphiti-mon316` profile.
- Create on Mini, not committed: `/Volumes/SSD/graphiti-mon316/runtime/`
  - Mini runtime checkout/config/log support area.
- Create on Mini, not committed: `~/.secrets/graphiti.env`
  - Compose-compatible secret file, generated by reading existing `~/.secrets/mcp.env` without printing the key.
- Create on Mini, not committed: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316.plist`
  - User LaunchAgent for Graphiti runtime supervision.
- Create on Mini, not committed: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-awake.plist`
  - User LaunchAgent running `/usr/bin/caffeinate -ims` to prevent idle/system/disk sleep while the user session exists.
- Create on Mini, not committed: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-tailnet-proxy.plist`
  - User LaunchAgent running the Tailnet SSH forward from `100.72.169.59:8018` to `127.0.0.1:18018`.
- Modify: `docs/graphiti-falkordb.md`
  - Replace MacBook-local runtime guidance with Mac Mini SSD deployment guidance.
- Modify: `docs/graphiti-falkordb-pilot-results.md`
  - Record Mini preflight, SSD sizing decision, and deployment verification results.
- Optional modify: `tests/test_graphiti_client.py`
  - Keep as a unit test only if it is not MacBook-pilot-specific. Otherwise leave the preserved copy under `docs/pilot/macbook/`.

## Not Included In This Version

- **Moving Milvus to the SSD:** not included. Milvus data is only `637 MB` and already running on the default Colima profile. Moving it would add risk without unblocking Graphiti.
- **Using `/Volumes/Mac Storage`:** not included. It is not user-writable and appears related to Time Machine/APFS storage.
- **Changing Claude Desktop configuration:** not included. Project rules forbid Claude Desktop changes unless explicitly requested.
- **Automatic prompt injection:** not included. Graphiti remains an optional derived sidecar until the pilot proves useful.
- **Kuzu backend:** not included. The current runtime choice remains Graphiti + FalkorDB.
- **Admin-level auto-login/power changes without credentials:** not included. If sudo/admin access is required, stop and report the exact command that needs an interactive admin session.

## Acceptance Criteria

- Graphiti runtime state lives under `/Volumes/SSD/graphiti-mon316`, not the internal `~/.colima`.
- Existing `milvus-standalone` continues running before and after Graphiti deployment.
- Dedicated Colima profile `graphiti-mon316` starts with `20 GiB` disk, Docker runtime, and a clearly scoped `COLIMA_HOME`.
- Graphiti health succeeds locally on the Mini at `http://127.0.0.1:18018/health`.
- FalkorDB is not exposed on the LAN or tailnet.
- Tailnet access exposes only the Graphiti HTTP endpoint at `100.72.169.59:8018`.
- MacBook can reach Graphiti over the Tailnet at `http://dom-kamet.tailf78a36.ts.net:8018/health`.
- MacBook MCP clients can connect to `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018`.
- MCP tool discovery returns the expected Graphiti tools or a documented compatible superset.
- A probe episode can be added to a temporary probe group, found via search, and cleaned up without touching non-probe data.
- A user-level awake LaunchAgent is loaded and verified.
- Reboot-without-login status is explicitly classified as either verified or blocked. Do not claim always-on across reboot unless it is proven.

## Task 1: Final Mini Preflight

**Files:**
- No file edits.

- [ ] **Step 1: Verify target machine identity**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'tailscale ip -4; test -d ~/Projects/milvus-standalone && echo mini_confirmed'
```

Expected: IP is `100.72.169.59` or current Tailscale Mini IP, and `mini_confirmed` prints.

- [ ] **Step 2: Verify SSD and internal disk**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'df -h /Volumes/SSD /Users/dominicmonkhouse; test -w /Volumes/SSD && echo SSD_writable'
```

Expected: `/Volumes/SSD` has hundreds of GB free and is writable. Internal disk may remain around `33 GiB` free.

- [ ] **Step 3: Verify no Graphiti collisions**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'lsof -nP -iTCP:8018 -sTCP:LISTEN || true; docker compose ls --all --format json | grep graphiti-mon316 || true; COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home colima list 2>/dev/null || true'
```

Expected: no listener on `8018`, no existing Graphiti Compose project, no unexpected existing `graphiti-mon316` profile.

- [ ] **Step 4: Verify Milvus before touching Graphiti**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'docker compose -f ~/Projects/milvus-standalone/docker-compose.yml ps; curl -fsS http://127.0.0.1:9091/healthz || true'
```

Expected: Milvus containers are running and healthy. If not, stop and fix Milvus first only if that is in scope.

## Task 2: Create SSD-Backed Colima Profile

**Files:**
- Create on Mini: `/Volumes/SSD/graphiti-mon316/colima-home/`
- No repo edits.

- [ ] **Step 1: Create the SSD runtime root**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'mkdir -p /Volumes/SSD/graphiti-mon316/colima-home /Volumes/SSD/graphiti-mon316/runtime /Volumes/SSD/graphiti-mon316/logs; chmod 700 /Volumes/SSD/graphiti-mon316/colima-home'
```

Expected: directories exist and are owned by `dominicmonkhouse`.

- [ ] **Step 2: Start a dedicated Colima profile**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home colima start graphiti-mon316 --runtime docker --cpu 2 --memory 4 --disk 20 --mount /Users/dominicmonkhouse:w --mount /Volumes/SSD:w'
```

Expected: profile starts successfully. If HFS/noowners causes VM-state issues, stop and revise to an APFS sparsebundle/disk-image on `/Volumes/SSD` before proceeding.

- [ ] **Step 3: Verify the profile**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home colima list; COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home colima status graphiti-mon316; find /Volumes/SSD/graphiti-mon316/colima-home -name docker.sock -type s -print'
```

Expected: profile `graphiti-mon316` shows `Running`, `2 CPU`, `4 GiB`, `20 GiB`, Docker runtime, and a dedicated profile Docker socket exists under `/Volumes/SSD/graphiti-mon316/colima-home/`.

- [ ] **Step 4: Verify existing Milvus is unaffected**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'docker compose -f ~/Projects/milvus-standalone/docker-compose.yml ps'
```

Expected: Milvus still runs under the default Colima context.

## Task 3: Add Deployment Files

**Files:**
- Create: `deploy/graphiti/docker-compose.yml`
- Create: `deploy/graphiti/docker-compose.mini.yml`
- Create: `deploy/graphiti/env.example`
- Create: `bin/start-graphiti-mon316.sh`
- Create: `bin/stop-graphiti-mon316.sh`

- [ ] **Step 1: Read upstream Graphiti MCP Compose source**

Run:

```bash
test -d /Users/dominicmonkhouse/Projects/graphiti/.git || git clone https://github.com/getzep/graphiti.git /Users/dominicmonkhouse/Projects/graphiti
git -C /Users/dominicmonkhouse/Projects/graphiti fetch --all --prune
find /Users/dominicmonkhouse/Projects/graphiti -maxdepth 3 -iname '*compose*.yml' -o -iname '*compose*.yaml'
```

Expected: upstream Compose route is found and read before writing local files. Use Graphiti's separate FalkorDB route, `mcp_server/docker/docker-compose-falkordb.yml`, not the all-in-one `docker-compose.yml`, because this deployment should run `falkordb` and `graphiti-mcp` as separate services.

- [ ] **Step 2: Write Compose files**

The Compose files must:
- use a fixed project name at runtime: `graphiti-mon316`;
- bind Graphiti to `127.0.0.1:18018:8000`;
- set `FALKORDB_URI=redis://falkordb:6379` for the `graphiti-mcp` service;
- keep FalkorDB Redis port `6379` unbound or bound to `127.0.0.1` only;
- set `BROWSER=0` to disable the FalkorDB browser UI;
- remove the FalkorDB browser UI host mapping for port `3000`, or bind it to `127.0.0.1` only if local debugging is explicitly needed;
- use top-level Compose volumes with explicit `name:` values `graphiti_mon316_falkordb_data` and `graphiti_mon316_mcp_logs`, so Docker Compose does not add an unexpected project-name prefix;
- load secrets from absolute host env file path `/Users/dominicmonkhouse/.secrets/graphiti.env` on the Mini;
- pass `OPENAI_API_KEY` into the `graphiti-mcp` container through that env file, matching upstream Graphiti expectations;
- avoid committing real secrets.

- [ ] **Step 3: Write start/stop scripts**

`bin/start-graphiti-mon316.sh` must:
- set `COLIMA_HOME=/Volumes/SSD/graphiti-mon316/colima-home`;
- start `colima start graphiti-mon316` only if needed;
- discover and export the dedicated profile Docker socket before running Docker commands, for example by finding `docker.sock` under `$COLIMA_HOME`;
- set `DOCKER_HOST=unix://<dedicated-profile-socket>`;
- fail if `DOCKER_HOST` points at the default `~/.colima/default/docker.sock`;
- use the exact Compose files from the repo checkout;
- run `docker compose -p graphiti-mon316 ... up -d`;
- write logs to `/Volumes/SSD/graphiti-mon316/logs`.

`bin/stop-graphiti-mon316.sh` must:
- set the same `COLIMA_HOME` and dedicated-profile `DOCKER_HOST`;
- run `docker compose -p graphiti-mon316 ... down` without `-v`;
- not delete volumes;
- not stop or touch the default Colima/Milvus profile.

- [ ] **Step 4: Shellcheck or syntax-check scripts**

Run:

```bash
bash -n bin/start-graphiti-mon316.sh
bash -n bin/stop-graphiti-mon316.sh
```

Expected: no syntax errors.

## Task 4: Prepare Mini Checkout and Secrets

**Files:**
- Create on Mini: `~/Projects/memsearch-mon316-graphiti-mini`
- Create on Mini: `~/.secrets/graphiti.env`

- [ ] **Step 1: Create or update Mini checkout**

Use the current branch source. Do not overwrite a dirty Mini checkout without reading it first.

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'test -d ~/Projects/memsearch-mon316-graphiti-mini/.git && git -C ~/Projects/memsearch-mon316-graphiti-mini status --short --branch || echo mini_checkout_missing'
```

Expected: either a clean existing checkout or a missing checkout. If dirty, stop and inspect before changing it.

- [ ] **Step 2: Transfer the deployment branch**

Check whether the current commit is already available from a remote branch:

```bash
git branch -r --contains HEAD
```

If the branch is already pushed, fetch or pull that branch on the Mini. If it is not pushed, do not push without explicit approval. Use archive transfer instead:

```bash
git archive HEAD | ssh dom-kamet.tailf78a36.ts.net 'mkdir -p ~/Projects/memsearch-mon316-graphiti-mini && cd ~/Projects/memsearch-mon316-graphiti-mini && tar xf -'
```

Expected: the Mini checkout contains the same `deploy/graphiti/` and `bin/` files that passed local syntax checks.

- [ ] **Step 3: Create Graphiti secret file without printing secrets**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'mkdir -p ~/.secrets; awk "/^OPENAI_API_KEY=/{print; found=1} END{if(!found) exit 42}" ~/.secrets/mcp.env > ~/.secrets/graphiti.env.tmp && mv ~/.secrets/graphiti.env.tmp ~/.secrets/graphiti.env && chmod 600 ~/.secrets/graphiti.env && awk "BEGIN{found=0} /^OPENAI_API_KEY=/{found=1} END{if(found) print \"graphiti secret ok\"; else exit 1}" ~/.secrets/graphiti.env'
```

Expected: `graphiti secret ok`. No key value printed.

## Task 5: User-Level Always-Awake and Service Supervision

**Files:**
- Create on Mini: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-awake.plist`
- Create on Mini: `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316.plist`

- [ ] **Step 1: Create an awake LaunchAgent**

Use `/usr/bin/caffeinate -ims` so display sleep is not blocked, but idle/system/disk sleep is blocked while the user session exists.

Expected plist fields:
- `Label`: `com.monkhouse.graphiti-mon316-awake`
- `ProgramArguments`: `/usr/bin/caffeinate`, `-ims`
- `RunAtLoad`: true
- `KeepAlive`: true

- [ ] **Step 2: Load and verify awake agent**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-awake.plist 2>/dev/null || launchctl kickstart -k gui/$(id -u)/com.monkhouse.graphiti-mon316-awake; launchctl print gui/$(id -u)/com.monkhouse.graphiti-mon316-awake | grep -E "state =|pid =|last exit code"'
```

Expected: agent is running and `pmset -g assertions` shows a `caffeinate` assertion.

- [ ] **Step 3: Create Graphiti LaunchAgent**

Expected plist fields:
- `Label`: `com.monkhouse.graphiti-mon316`
- `ProgramArguments`: `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti-mini/bin/start-graphiti-mon316.sh`
- `RunAtLoad`: true
- `StartInterval`: `60`
- no `KeepAlive` dictionary for this agent. The start script runs `docker compose up -d` and exits, so supervision is periodic idempotent reconciliation rather than a long-lived foreground process.
- stdout/stderr logs under `/Volumes/SSD/graphiti-mon316/logs/`.

- [ ] **Step 4: Verify reboot/login limitation**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser 2>/dev/null || echo autoLoginUser_missing; test -f /etc/kcpassword && echo kcpassword_present || echo kcpassword_missing; sudo -n true >/dev/null 2>&1 && echo sudo_available || echo sudo_unavailable'
```

Expected: if auto-login remains missing and sudo unavailable, document that the service is login-session always-on, not reboot-without-login always-on.

## Task 6: Start Graphiti and Expose via Tailscale

**Files:**
- No additional repo edits unless verification changes docs.

- [ ] **Step 1: Start Graphiti**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net '~/Projects/memsearch-mon316-graphiti-mini/bin/start-graphiti-mon316.sh'
```

Expected: Compose project `graphiti-mon316` is running in the SSD-backed Colima profile.

- [ ] **Step 2: Verify local health**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'curl -fsS http://127.0.0.1:18018/health'
```

Expected: Graphiti health succeeds through the deployed `127.0.0.1:18018` container binding.

- [ ] **Step 3: Configure Tailnet SSH forward**

Tailscale Serve is not enabled on the Tailnet, so the verified route is a supervised SSH local forward.

```bash
ssh dom-kamet.tailf78a36.ts.net 'launchctl print gui/$(id -u)/com.monkhouse.graphiti-mon316-tailnet-proxy | grep -E "state =|pid =|last exit code"'
```

Expected URLs:
- Health: `http://dom-kamet.tailf78a36.ts.net:8018/health`
- MCP: `http://dom-kamet.tailf78a36.ts.net:8018/mcp`

- [ ] **Step 4: Verify Tailnet path passthrough**

Run from the MacBook:

```bash
curl -fsS http://dom-kamet.tailf78a36.ts.net:8018/health
```

Expected: Graphiti health succeeds through the Tailnet SSH forward. MCP tool discovery in Task 7 must use `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018`.

- [ ] **Step 5: Verify Funnel is off**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'tailscale funnel status 2>&1 || true'
```

Expected: no Funnel config.

## Task 7: Probe Graphiti MCP

**Files:**
- Modify: `docs/graphiti-falkordb-pilot-results.md`

- [ ] **Step 1: Verify MCP tools**

From MacBook, hit the selected tailnet endpoint and confirm tools include:
- `add_memory`
- `search_nodes`
- `search_memory_facts`
- `delete_entity_edge`
- `delete_episode`
- `get_entity_edge`
- `get_episodes`
- `clear_graph`
- `get_status`

Endpoint for this deployment:

```text
http://dom-kamet.tailf78a36.ts.net:8018/mcp
Host: 127.0.0.1:18018
```

- [ ] **Step 2: Add a temporary probe episode**

Use group id:

```text
ms_memsearch_probe_<timestamp>
```

Do not use `ms_memsearch_ae2d4f9b` until the isolated probe passes.

- [ ] **Step 3: Search and verify provenance**

Expected: `search_memory_facts` returns the probe fact and the assigned Graphiti episode UUID appears in the fact's `episodes` array.

- [ ] **Step 4: Clean only the probe group**

Clear/delete only the temporary probe data and verify scoped `get_episodes` for the probe group is empty. Do not clear any non-probe graph.

## Task 8: Update Docs and Linear

**Files:**
- Modify: `docs/graphiti-falkordb.md`
- Modify: `docs/graphiti-falkordb-pilot-results.md`
- Optional modify: `tests/test_graphiti_client.py`

- [ ] **Step 1: Update operator guide**

Record:
- SSD-backed `COLIMA_HOME`;
- profile name `graphiti-mon316`;
- 20 GiB disk sizing rationale;
- Tailnet URLs: `http://dom-kamet.tailf78a36.ts.net:8018/health` and `http://dom-kamet.tailf78a36.ts.net:8018/mcp`;
- MCP Host header requirement: `Host: 127.0.0.1:18018`;
- LaunchAgent labels;
- rollback commands;
- explicit always-on limitation if auto-login/admin power settings remain unresolved.

- [ ] **Step 2: Update pilot results**

Record exact:
- Mini preflight outputs;
- Compose project status;
- health output;
- tool list;
- probe UUID;
- cleanup verification;
- Milvus unaffected check.

- [ ] **Step 3: Update MON-316**

Update Linear issue `MON-316` with:
- this plan path;
- selected SSD/20 GiB deployment route;
- verification status;
- remaining admin-only power/login blocker if any.

## Rollback

- Boot out only Graphiti user agents:

```bash
ssh dom-kamet.tailf78a36.ts.net 'launchctl bootout gui/$(id -u)/com.monkhouse.graphiti-mon316 2>/dev/null || true; launchctl bootout gui/$(id -u)/com.monkhouse.graphiti-mon316-awake 2>/dev/null || true'
```

- Boot out only the Tailnet forward agent after reading current listener status:

```bash
ssh dom-kamet.tailf78a36.ts.net 'launchctl print gui/$(id -u)/com.monkhouse.graphiti-mon316-tailnet-proxy | grep -E "state =|pid =|last exit code"; launchctl bootout gui/$(id -u)/com.monkhouse.graphiti-mon316-tailnet-proxy 2>/dev/null || true'
```

- Stop only Graphiti Compose:

```bash
ssh dom-kamet.tailf78a36.ts.net '~/Projects/memsearch-mon316-graphiti-mini/bin/stop-graphiti-mon316.sh'
```

- Do not use `docker compose down -v`.
- Do not remove named volumes without explicit approval.
- Do not stop or delete default Colima/Milvus.
- Do not delete `/Volumes/SSD/graphiti-mon316` without explicit approval.

## Risks and Mitigations

- **HFS/noowners on `/Volumes/SSD`:** Start with a Colima smoke test. If it fails, use an APFS sparsebundle/disk image stored on `/Volumes/SSD` rather than falling back to the internal disk.
- **Reboot-without-login gap:** User LaunchAgents require a user session. Without auto-login or an admin-level daemon/power configuration, call the service login-session always-on only.
- **Resource contention with Milvus:** Use a separate Colima home/profile and start at `2 CPU / 4 GiB / 20 GiB`. Increase only with evidence.
- **Tailscale exposure mistake:** Bind Docker to localhost and use the supervised Tailnet SSH forward. Keep Funnel off.
- **Graph wipe risk:** Use a temporary probe group and never run broad `clear_graph` against the real group.
- **Secrets leakage:** Never print `OPENAI_API_KEY`. Derive `~/.secrets/graphiti.env` from `~/.secrets/mcp.env` with `awk` checks only.

## AP Review Fixes

- Attempt 1 accepted Claude's Docker context objection: start/stop scripts must set the SSD-backed `COLIMA_HOME`, discover the dedicated profile Docker socket, export `DOCKER_HOST`, and fail if Docker points at the default Milvus Colima socket.
- Attempt 1 accepted Claude's upstream Compose objection: the plan now pins Graphiti's separate `docker-compose-falkordb.yml` route, uses `FALKORDB_URI=redis://falkordb:6379`, and replaces the invented Graphiti state volume with explicit `falkordb_data` and `mcp_logs` volume names.
- Attempt 1 accepted Claude's FalkorDB UI objection: the Mini override must set `BROWSER=0` and remove or localhost-bind port `3000`.
- Attempt 1 originally accepted Claude's Tailscale ambiguity objection with HTTPS Serve. During execution, Tailscale Serve proved disabled on the Tailnet, so the final verified route is the supervised SSH forward at `http://dom-kamet.tailf78a36.ts.net:8018/mcp` with `Host: 127.0.0.1:18018`.
- Attempt 1 accepted Claude's LaunchAgent objection: the Graphiti LaunchAgent now uses `RunAtLoad` plus `StartInterval=60` for idempotent reconciliation, not a `KeepAlive` dictionary around a background `docker compose up -d` process.
- Attempt 1 accepted Claude's env file objection: the Compose file must use absolute host env file path `/Users/dominicmonkhouse/.secrets/graphiti.env` and pass `OPENAI_API_KEY` into `graphiti-mcp`.
- Attempt 1 accepted Claude's Mini transfer objection: the plan now checks whether `HEAD` is remote-available and otherwise uses `git archive HEAD | ssh ... tar xf -` without pushing.
- Attempt 2 returned `CLEAN PASS`: Claude re-read this plan and verified all 8 accepted attempt 1 objections are resolved in the current text.

## Review Status

- Plan written after live Mac Mini preflight and upstream Colima/FalkorDB documentation checks.
- Plan-document review: not run because Codex subagent spawning is not authorised unless explicitly requested by the user in this runtime.
- Cross-model adversarial review: clean pass via ap-check on attempt 2. Claude verified Docker context routing, upstream Compose selection, FalkorDB UI exposure, Tailscale Serve mode, LaunchAgent strategy, env file handling, Mini transfer, and `BROWSER=0`.
- Linear handoff: MON-316 — https://linear.app/monkhouseandcompany/issue/MON-316/graphiti-falkordb-memory-layer-implementation-plan
