# Graphiti MemSearch Keepalive Freshness Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Mac Mini automation that keeps Graphiti/FalkorDB running, keeps MemSearch vector sources fresh, and promotes only reviewed capped curated facts into Graphiti.

**Architecture:** Keep Markdown as canonical memory and Milvus/vector search as the primary automatic recall layer. Harden the existing Mac Mini Graphiti sidecar with Docker restart policy, a targeted watchdog, and verified LaunchAgent deployment, while adding a review-gated Graphiti candidate and capped-ingest workflow rather than blind raw-memory graph ingestion. Source freshness remains automatic for Linear and Manus vector cards; Graphiti freshness becomes candidate-first, evidence-cited, capped, evaluated, and rollback-ready.

**Tech Stack:** macOS LaunchAgents, Tailscale Serve, Colima, Docker Compose, FalkorDB, Graphiti MCP, Python 3.10+, Click, pytest, ruff, MemSearch CLI, Linear MCP/API tracking.

---

## Scope Check

This is big enough for full plan ceremony.

- Cross-machine: MacBook planning and Mac Mini runtime.
- Cross-system: LaunchAgents, Tailscale Serve, Docker/Colima, Graphiti, FalkorDB, Milvus/MemSearch, Linear/Manus source sync.
- High blast radius if wrong: a bad graph-ingest job can convert stale troubleshooting notes into current operational facts.
- More than 10 atomic tasks.
- Needs rollback gates, not just a mechanical edit.

This plan is plan-only. Do not edit runtime configs, install LaunchAgents, restart services, or ingest Graphiti batches until Dom explicitly approves execution.

## Evidence Checked

### Local and Mini state

- Existing repo: `/Users/dominicmonkhouse/Projects/memsearch`.
- Existing research deliverable: `/Users/dominicmonkhouse/Projects/memsearch/outputs/2026-06-14/graphiti-memsearch-keepalive-freshness-plan.html`.
- Existing source freshness docs: `/Users/dominicmonkhouse/Projects/memsearch/docs/source-freshness-automation.md`.
- Existing Graphiti deployment scripts:
  - `/Users/dominicmonkhouse/Projects/memsearch/bin/start-graphiti-mon316.sh`
  - `/Users/dominicmonkhouse/Projects/memsearch/bin/stop-graphiti-mon316.sh`
- Existing Graphiti Compose files:
  - `/Users/dominicmonkhouse/Projects/memsearch/deploy/graphiti/docker-compose.yml`
  - `/Users/dominicmonkhouse/Projects/memsearch/deploy/graphiti/docker-compose.mini.yml`
- Existing source scheduler renderer:
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/scheduler.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/cli.py`
- Existing curated Graphiti guardrails:
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/graphiti/curated.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_cli.py`
  - `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_curated.py`
- Mini process manager verification:
  - `pm2` is not present.
  - Graphiti and source-sync are managed by LaunchAgents.
  - Docker containers show Graphiti/FalkorDB and Milvus health.
- Mini runtime verification:
  - Graphiti health endpoint returned `{"status":"healthy","service":"graphiti-mcp"}` at `127.0.0.1:18018`.
  - Tailscale Serve forwards TCP `8018 -> 127.0.0.1:18018`.
  - `com.monkhouse.graphiti-mon316` has `RunAtLoad=true`, `StartInterval=60`, last exit `0`.
  - `com.monkhouse.graphiti-mon316-awake` runs `caffeinate -ims` with `KeepAlive=true`.
  - Linear daily sync LaunchAgent has run with last exit `0`.
  - Manus weekly sync LaunchAgent exists but has not yet reached its weekly slot.
- Important gap:
  - Mini `~/Projects/memsearch` returned `No such command 'graph-status'`.
  - MacBook repo has `graph-status`, `graph-eval`, `graph-index-curated`, and graph-on search code.

### Upstream and community evidence

- Graphiti supports incremental graph updates without full recomputation, but that does not decide which memories are safe to promote: https://help.getzep.com/graphiti/getting-started/welcome
- Graphiti MCP exposes episode management, fact/node search, group filtering, and graph maintenance: https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- FalkorDB Graphiti docs call out persistent storage, volume correctness, consistent graph names, resource monitoring, and backups: https://docs.falkordb.com/agentic-memory/graphiti-mcp-server.html
- Tailscale Serve is the correct tailnet-only exposure model. `--bg` persists and resumes after reboot or Tailscale restart: https://tailscale.com/docs/reference/tailscale-cli/serve
- Apple launchd docs confirm user LaunchAgents run only while the user is logged in, and network availability cannot be assumed at job start: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- Docker Compose supports `healthcheck`, `depends_on: condition: service_healthy`, named volumes, and `restart: unless-stopped`: https://docs.docker.com/reference/compose-file/services/ and https://docs.docker.com/compose/how-tos/startup-order/
- Graphiti issue #1452 documents FalkorDB data-loss risk when the Docker volume is mounted at the wrong path. The current local compose file already uses the safer `/var/lib/falkordb/data` path: https://github.com/getzep/graphiti/issues/1452
- Reddit/community threads reinforce that Docker health checks alone are not self-healing and that Mac Mini pre-login uptime requires system-level setup:
  - https://www.reddit.com/r/docker/comments/16x7xcw/healthcheck_to_restart_container/
  - https://www.reddit.com/r/Tailscale/comments/1l6rko9/how_to_make_tailscale_reliably_autostart_on_a/

## Current System Boundaries

- Graphiti/FalkorDB is a derived sidecar, not canonical memory.
- Markdown remains canonical.
- Milvus/vector search remains the primary automatic recall path.
- Linear and Manus source freshness can remain automatic into vector search.
- Graphiti curated graph updates must remain reviewed, capped, evaluated, and rollback-ready.
- Do not ingest full `.memsearch/memory` into Graphiti.
- Do not expose FalkorDB on the LAN or tailnet.
- Do not claim reboot-without-login reliability until an approved reboot test proves it.
- Do not modify Claude Desktop config.

## File Structure

### Files to modify

- `deploy/graphiti/docker-compose.yml`
  - Add container restart policy.
  - Keep existing FalkorDB persistence path.
  - Add labels if useful for watchdog filtering.

- `pyproject.toml`
  - Add `pyyaml` to the dev/test dependency group if the compose test uses `yaml.safe_load`.
  - Do not rely on an undeclared transitive dependency.

- `src/memsearch/backfill/scheduler.py`
  - Extend scheduler rendering to include Graphiti watchdog, freshness proof, and candidate-report jobs.
  - Render Graphiti Mini-only jobs only when `machine` identifies Dominic's Mac mini.
  - Keep actual install approval-gated.

- `src/memsearch/backfill/cli.py`
  - Add CLI commands for Graphiti watchdog, candidate report, and freshness proof wrappers if they belong under backfill operations.
  - If the graph-specific command belongs in `src/memsearch/cli.py` instead, keep thin wrappers here and route to graph modules.

- `src/memsearch/cli.py`
  - Add or expose any graph operation commands needed by automation, such as candidate reporting or backup checks, if not better placed under `backfill.cli`.

- `docs/source-freshness-automation.md`
  - Document new watchdog, freshness proof, candidate report, and approval-gated graph ingest flow.

- `docs/graphiti-falkordb.md`
  - Document runtime hardening and the exact Mini health/recovery commands.

- `.gitignore`
  - Only modify if new local state/log/checkpoint paths are not already ignored.

### Files to create

- `src/memsearch/graphiti/watchdog.py`
  - Pure Python health/recovery helpers for Graphiti runtime checks.
  - Must define `collect_checks()` and `run_recovery_commands(commands)` because CLI tests and command wiring patch those functions directly.

- `src/memsearch/graphiti/candidates.py`
  - Candidate generation and current-state risk classification for curated graph facts.

- `src/memsearch/graphiti/backup.py`
  - Non-destructive persistence/backup helpers for FalkorDB runtime state, if this cannot stay as shell-only operational docs.

- `tests/test_graphiti_watchdog.py`
  - Unit tests for health parsing, recovery decision logic, and no-Milvus-touch guardrails.

- `tests/test_graphiti_candidates.py`
  - Unit tests for candidate selection, rejection, evidence requirements, and stale route controls.

- `tests/backfill_chats/test_graphiti_scheduler.py`
  - Scheduler plist tests for new LaunchAgents.

- `bin/graphiti-watchdog-mon316.sh`
  - Mini wrapper that sources expected environment, sets the dedicated `graphiti-mon316` Colima Docker socket, runs the MemSearch watchdog command, and logs to SSD with a home-directory fallback if the SSD is missing.

- `bin/graphiti-candidate-report-mon316.sh`
  - Mini wrapper that generates review reports without mutating Graphiti.

- `bin/graphiti-backup-mon316.sh`
  - Mini wrapper that sets the dedicated `graphiti-mon316` Colima Docker socket and runs the nightly Graphiti/FalkorDB backup job.

- `bin/graphiti-source-freshness-proof-mon316.sh`
  - Mini wrapper around source-freshness proof logging.

- `docs/graphiti-candidate-reports/README.md`
  - Short operator note for candidate report artefacts, if reports are stored in repo docs. Prefer ignored `outputs/` for dated reports.

### Runtime files created on the Mini during execution

These must not be committed.

- `/Volumes/SSD/graphiti-mon316/logs/watchdog.log`
- `/Volumes/SSD/graphiti-mon316/logs/backup.log`
- `/Volumes/SSD/graphiti-mon316/logs/candidate-report.log`
- `/Volumes/SSD/graphiti-mon316/logs/source-freshness-proof.log`
- `/Volumes/SSD/graphiti-mon316/state/watchdog.json`
- `/Volumes/SSD/graphiti-mon316/backups/<timestamp>/`
- `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-watchdog.plist`
- `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-backup.plist`
- `~/Library/LaunchAgents/com.memsearch.source-freshness-proof.plist`
- `~/Library/LaunchAgents/com.memsearch.graphiti-candidate-report.plist`

## Not Included In This Version

- **Blind Graphiti ingestion of `.memsearch/memory`:** excluded because previous broad ingestion produced stale current-state facts from historical troubleshooting.
- **Automatic live graph ingest without review:** excluded until at least two candidate-report cycles produce clean evidence and manual capped batches pass evaluation.
- **Replacing vector search with Graphiti:** excluded. Graphiti remains a derived sidecar.
- **Exposing FalkorDB to the tailnet:** excluded. Only Graphiti HTTP stays bound through localhost and Tailscale Serve.
- **System LaunchDaemons or reboot-before-login hardening:** excluded from this implementation. That requires a separate admin/power/login approval gate.
- **Claude Desktop config changes:** excluded by standing rule.
- **Full backup restore automation against production graph:** deferred. This plan includes non-destructive backup and a separate temporary restore drill only.

## Deferred Decisions

- **Alert destination:** choose between logs only, email, Linear comments, or a morning-briefing note. This plan implements logs and structured state first.
- **Canonical Mini checkout:** current recommendation is `~/Projects/memsearch`, but execution must first decide whether to promote graph-enabled code there or keep `/Users/dominicmonkhouse/Projects/memsearch-mon316-graphiti-mini` as the runtime checkout. Do not leave both ambiguous.
- **Graphiti ingest automation level:** start manual/approval-triggered. Revisit after two clean weekly candidate reports and at least one successful capped manual ingest.
- **Reboot-without-login:** separate admin plan only.

## Acceptance Criteria

- Linear issue `MON-348` exists before implementation starts, and every implementation commit message uses that issue identifier.
- Mini `~/Projects/memsearch` or the chosen runtime checkout exposes `graph-status`, `graph-eval`, `graph-index-curated`, and graph-on search.
- Graphiti and FalkorDB Compose services include Docker restart policy.
- Watchdog can detect and recover a stopped Graphiti MCP container without touching Milvus/default Colima.
- Watchdog verifies local health, tailnet health, Docker socket, Compose health, Tailscale Serve status, and SSD free space.
- Source freshness proof runs after the Linear daily sync and logs proof search results.
- Weekly Graphiti candidate report generates evidence-cited candidates without mutating Graphiti.
- Every candidate statement is classified as `current`, `historical`, `superseded`, or `unsafe`; only `current` statements can become ingest seeds by default.
- Candidate report rejects raw transcripts, raw Manus exports, full `.memsearch/memory`, stale routes, and unsafe troubleshooting symptoms by default.
- Capped graph ingest remains approval-gated, dry-run-first, manifest-checkpointed, evaluated, and rollback-ready.
- FalkorDB nightly backup job is scheduled, produces a dated backup artefact, and a restore drill can recover probe data in a temporary non-production graph group or separate project.
- FalkorDB backups use a consistent snapshot mechanism, have an explicit retention policy, and never live-copy an active volume without a database-level save/checkpoint.
- Docs state exactly what is user-session-supervised versus reboot-without-login verified.
- Linear issue tracks the plan and execution progress.

## Implementation Prerequisite: Linear Tracking

Before Task 1 starts, load Linear issue `MON-348` for this plan and confirm every task commit message uses that identifier.

- Team: `MON`
- Title: `Graphiti MemSearch Keepalive Freshness Automation Implementation Plan`
- Description must include:
  - Plan path: `/Users/dominicmonkhouse/Projects/memsearch/docs/superpowers/plans/2026-06-14-graphiti-memsearch-keepalive-freshness-automation.md`
  - Goal: `Build the Mac Mini automation that keeps Graphiti/FalkorDB running, keeps MemSearch vector sources fresh, and promotes only reviewed capped curated facts into Graphiti.`
  - Execution instruction: load this issue first, verify it references the same local plan path, and write progress back to Linear after every task.

No implementation commit is valid unless it references `MON-348`.

## Task 1: Runtime Checkout Parity

**Files:**
- Modify: none initially.
- Verify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
- Verify on Mini: `~/Projects/memsearch`, `~/Projects/memsearch-mon316-graphiti-mini`

- [ ] **Step 1: Fetch current repo state on MacBook**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git fetch fork main
git status --short
git log --oneline -5
```

Expected: local branch is known, unrelated dirty files are recorded, and graph CLI code is present in `src/memsearch/cli.py`.

- [ ] **Step 2: Verify graph CLI commands on MacBook**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run memsearch --help | grep -E "graph-status|graph-eval|graph-index-curated"
```

Expected: all three commands print.

- [ ] **Step 3: Verify graph CLI commands on Mini**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch --help | grep -E "graph-status|graph-eval|graph-index-curated"'
```

Expected today: likely fails until the Mini checkout is updated. Record the exact output.

- [ ] **Step 4: Decide and document canonical Mini checkout**

If `~/Projects/memsearch` is behind, use it as canonical unless there is evidence the Mini-specific checkout contains unmerged runtime-only changes.

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'for d in ~/Projects/memsearch ~/Projects/memsearch-mon316-graphiti-mini; do echo "__DIR__:$d"; test -d "$d" && (cd "$d" && git status --short 2>/dev/null || echo "not git"); done'
```

Expected: one checkout is selected as canonical in the Linear issue before any scheduler paths are changed.

- [ ] **Step 5: Sync chosen checkout after approval**

If using `~/Projects/memsearch`, deploy code only after confirming the plan is approved.

Run after approval:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && git pull --ff-only fork main && /Users/dominicmonkhouse/.local/bin/uv sync'
```

Expected: graph CLI commands become available on the Mini.

- [ ] **Step 6: Commit if repo files changed**

If this task only updates the Mini checkout and no repo files changed, do not commit. If docs are updated to record the canonical checkout, commit only those docs:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add docs/graphiti-falkordb.md
git commit -m "docs: record graphiti mini runtime checkout"
```

Expected: no unrelated files staged.

## Task 2: Compose Restart Policy

**Files:**
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/deploy/graphiti/docker-compose.yml`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/pyproject.toml`
- Test: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_runtime_config.py`

- [ ] **Step 1: Write failing compose test**

Create `tests/test_graphiti_runtime_config.py` with:

```python
from __future__ import annotations

from pathlib import Path

import yaml


def test_graphiti_compose_has_restart_policy_and_persistent_falkordb_volume():
    compose = yaml.safe_load(Path("deploy/graphiti/docker-compose.yml").read_text())
    services = compose["services"]

    assert services["falkordb"]["restart"] == "unless-stopped"
    assert services["graphiti-mcp"]["restart"] == "unless-stopped"
    assert "falkordb_data:/var/lib/falkordb/data" in services["falkordb"]["volumes"]
    assert "6379:6379" not in str(services["falkordb"].get("ports", []))
```

Add `pyyaml` explicitly to the dev/test dependency group in `pyproject.toml` before this test is expected to pass. Do not rely on `yaml` being available transitively.

- [ ] **Step 2: Run failing test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_runtime_config.py -q
```

Expected: fails because `restart` is missing.

- [ ] **Step 3: Add restart policy**

Modify `deploy/graphiti/docker-compose.yml`:

```yaml
services:
  falkordb:
    restart: unless-stopped
    ...

  graphiti-mcp:
    restart: unless-stopped
    ...
```

Do not change volume names, `BROWSER`, env file handling, or port exposure.

- [ ] **Step 4: Run focused test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_runtime_config.py -q
```

Expected: pass.

- [ ] **Step 5: Validate Compose config**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
docker compose -p graphiti-mon316 -f deploy/graphiti/docker-compose.yml -f deploy/graphiti/docker-compose.mini.yml config >/tmp/graphiti-compose-config.yml
grep -n "restart: unless-stopped" /tmp/graphiti-compose-config.yml
grep -n "/var/lib/falkordb/data" /tmp/graphiti-compose-config.yml
```

Expected: restart appears for both services and FalkorDB data path remains correct.

- [ ] **Step 6: Run graphiti tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_runtime_config.py tests/test_graphiti_cli.py tests/test_graphiti_curated.py -q
uv run ruff check deploy/graphiti tests/test_graphiti_runtime_config.py
```

Expected: tests and lint pass.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add deploy/graphiti/docker-compose.yml tests/test_graphiti_runtime_config.py
git add pyproject.toml uv.lock
git commit -m "MON-348 harden graphiti compose restart policy"
```

Expected: commit references the Linear issue created from this plan.

## Task 3: Graphiti Watchdog Command

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/graphiti/watchdog.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_watchdog.py`

- [ ] **Step 1: Write failing decision-logic tests**

Create `tests/test_graphiti_watchdog.py`:

```python
from __future__ import annotations

from memsearch.graphiti.watchdog import WatchdogCheck, WatchdogDecision, decide_recovery


def test_watchdog_noops_when_all_checks_pass():
    checks = [
        WatchdogCheck("local_health", True, "ok"),
        WatchdogCheck("tailnet_health", True, "ok"),
        WatchdogCheck("colima_graphiti_mon316", True, "running"),
        WatchdogCheck("compose", True, "ok"),
        WatchdogCheck("tailscale_serve", True, "ok"),
        WatchdogCheck("ssd_space", True, "ok"),
    ]

    assert decide_recovery(checks) == WatchdogDecision(action="noop", reason="all checks passed")


def test_watchdog_restarts_graphiti_only_for_failed_health():
    checks = [
        WatchdogCheck("local_health", False, "connection refused"),
        WatchdogCheck("compose", True, "containers running"),
        WatchdogCheck("milvus", True, "healthy"),
    ]

    decision = decide_recovery(checks)

    assert decision.action == "restart_graphiti"
    assert "milvus" not in decision.commands
    assert any("start-graphiti-mon316.sh" in command for command in decision.commands)


def test_watchdog_reapplies_tailscale_serve_when_forward_missing():
    checks = [WatchdogCheck("tailscale_serve", False, "missing tcp 8018")]

    decision = decide_recovery(checks)

    assert decision.action == "repair_tailscale_serve"
    assert decision.commands == ["tailscale serve --bg --tcp=8018 tcp://127.0.0.1:18018"]
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_watchdog.py -q
```

Expected: fails because `memsearch.graphiti.watchdog` does not exist.

- [ ] **Step 3: Implement data model and recovery decision**

Create `src/memsearch/graphiti/watchdog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchdogCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class WatchdogDecision:
    action: str
    reason: str
    commands: tuple[str, ...] = ()


START_SCRIPT = "/Users/dominicmonkhouse/Projects/memsearch/bin/start-graphiti-mon316.sh"
TAILSCALE_REPAIR_COMMAND = "tailscale serve --bg --tcp=8018 tcp://127.0.0.1:18018"


def decide_recovery(checks: list[WatchdogCheck]) -> WatchdogDecision:
    failed = [check for check in checks if not check.ok]
    if not failed:
        return WatchdogDecision(action="noop", reason="all checks passed")

    failed_names = {check.name for check in failed}
    if "tailscale_serve" in failed_names and failed_names <= {"tailscale_serve"}:
        return WatchdogDecision(
            action="repair_tailscale_serve",
            reason="tailscale serve forward missing",
            commands=(TAILSCALE_REPAIR_COMMAND,),
        )

    if failed_names & {"local_health", "tailnet_health", "compose", "colima_graphiti_mon316"}:
        return WatchdogDecision(
            action="restart_graphiti",
            reason=", ".join(f"{check.name}: {check.detail}" for check in failed),
            commands=(START_SCRIPT,),
        )

    return WatchdogDecision(
        action="report_only",
        reason=", ".join(f"{check.name}: {check.detail}" for check in failed),
    )
```

This is intentionally pure logic first. Shell execution comes later and must be narrow.

- [ ] **Step 3a: Implement real check and recovery helpers**

In the same module, define these concrete helpers before wiring the CLI:

```python
def collect_checks() -> list[WatchdogCheck]:
    ...


def run_recovery_commands(commands: tuple[str, ...] | list[str]) -> list[dict[str, object]]:
    ...
```

`collect_checks()` must run the real health checks used by the CLI, including:

- local Graphiti health;
- tailnet Graphiti health when resolvable;
- dedicated Colima profile check for `graphiti-mon316`;
- Docker Compose service state using the dedicated Colima socket;
- `tailscale serve status --json`;
- `/Volumes/SSD` free space when that path exists.

`run_recovery_commands()` must execute only the commands returned by `decide_recovery()`, capture return code/stdout/stderr, and refuse any command string containing `milvus`, `down -v`, `docker volume rm`, or an empty command. This keeps the monkeypatch targets in the CLI tests real and prevents the command implementation from inventing a second execution path.

- [ ] **Step 4: Run tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_watchdog.py -q
```

Expected: pass.

- [ ] **Step 5: Add CLI watchdog command**

Add a `graph-watchdog` command to `src/memsearch/cli.py` that performs real checks and optionally executes the selected recovery action:

- runs checks when possible;
- supports `--dry-run`;
- supports `--execute`;
- supports `--json-output`;
- writes no runtime state unless `--state-path` is provided;
- never restarts Milvus;
- exits non-zero only when recovery fails, not when it successfully repairs Graphiti.

The command must check at least:

- `http://127.0.0.1:18018/health`;
- `http://dom-kamet.tailf78a36.ts.net:8018/health` when DNS is resolvable;
- `colima status graphiti-mon316` or the equivalent dedicated-profile health check;
- Docker Compose service state for the Graphiti project;
- `tailscale serve status --json`;
- `/Volumes/SSD` free space when that path exists.

The first implementation can mock shell execution in tests, but the command itself must be capable of real recovery when `--execute` is passed. Do not ship a help-only or dry-run-only command.

```python
@cli.command("graph-watchdog")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--execute", is_flag=True, default=False)
@click.option("--state-path", type=click.Path(path_type=Path), default=None)
@click.option("--json-output", is_flag=True, default=False)
def graph_watchdog(dry_run: bool, execute: bool, state_path: Path | None, json_output: bool) -> None:
    ...
```

- [ ] **Step 6: Test CLI behaviour**

Add tests to `tests/test_graphiti_cli.py` that prove more than help text:

```python
def test_graph_watchdog_dry_run_reports_restart_without_executing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: calls.extend(commands))

    result = CliRunner().invoke(cli, ["graph-watchdog", "--dry-run", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["decision"]["action"] == "restart_graphiti"
    assert calls == []


def test_graph_watchdog_execute_runs_recovery(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: calls.extend(commands))

    result = CliRunner().invoke(cli, ["graph-watchdog", "--execute", "--json-output"])

    assert result.exit_code == 0
    assert any("start-graphiti-mon316.sh" in command for command in calls)


def test_graph_watchdog_records_consecutive_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: [])

    state = tmp_path / "watchdog.json"

    result = CliRunner().invoke(cli, ["graph-watchdog", "--dry-run", "--state-path", str(state), "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(state.read_text())
    assert payload["consecutive_failures"] == 1
    assert payload["alert_required"] is False
```

If `consecutive_failures >= 3`, the JSON output and state file must set `alert_required: true` and include a human-readable `alert_reason`. This version may log that alert only; do not wire email, Linear comments, or other outbound notification until a later approved plan chooses the destination.

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_watchdog.py tests/test_graphiti_cli.py -q
```

Expected: pass.

- [ ] **Step 7: Full gate**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_watchdog.py tests/test_graphiti_cli.py tests/test_graphiti_curated.py -q
uv run ruff check src/memsearch/graphiti/watchdog.py src/memsearch/cli.py tests/test_graphiti_watchdog.py tests/test_graphiti_cli.py
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add src/memsearch/graphiti/watchdog.py src/memsearch/cli.py tests/test_graphiti_watchdog.py tests/test_graphiti_cli.py
git commit -m "MON-348 add graphiti watchdog command"
```

Expected: no unrelated files staged.

## Task 4: Watchdog Mini Wrapper and Scheduler Rendering

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/bin/graphiti-watchdog-mon316.sh`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/scheduler.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/backfill_chats/test_graphiti_scheduler.py`

- [ ] **Step 1: Write failing scheduler test**

Create `tests/backfill_chats/test_graphiti_scheduler.py`:

```python
from __future__ import annotations

import plistlib

from memsearch.backfill.scheduler import render_scheduler_plists


def test_scheduler_renders_graphiti_watchdog(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-watchdog" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.monkhouse.graphiti-mon316-watchdog.plist").read_bytes())
    assert payload["Label"] == "com.monkhouse.graphiti-mon316-watchdog"
    assert payload["StartInterval"] == 300
    assert payload["RunAtLoad"] is True
    assert "graphiti-watchdog-mon316.sh" in " ".join(payload["ProgramArguments"])


def test_scheduler_does_not_render_graphiti_mini_jobs_on_macbook(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's MacBook Pro")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-watchdog" not in labels
    assert "com.monkhouse.graphiti-mon316-backup" not in labels
    assert "com.memsearch.graphiti-candidate-report" not in labels
```

- [ ] **Step 2: Run failing test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_graphiti_scheduler.py -q
```

Expected: fails because the watchdog plist is not rendered.

- [ ] **Step 3: Create wrapper script**

Create `bin/graphiti-watchdog-mon316.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
FALLBACK_LOG_DIR="$HOME/Library/Logs/graphiti-mon316"
STATE_DIR="/Volumes/SSD/graphiti-mon316/state"
FALLBACK_STATE_DIR="$HOME/Library/Application Support/graphiti-mon316/state"
COLIMA_PROFILE="graphiti-mon316"
COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"
DOCKER_SOCK="$COLIMA_HOME/$COLIMA_PROFILE/docker.sock"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ ! -d /Volumes/SSD ]; then
  LOG_DIR="$FALLBACK_LOG_DIR"
  STATE_DIR="$FALLBACK_STATE_DIR"
fi

mkdir -p "$LOG_DIR" "$STATE_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/watchdog.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti watchdog start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
fi

if [ -S "$DOCKER_SOCK" ]; then
  export DOCKER_HOST="unix://$DOCKER_SOCK"
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] dedicated Docker socket missing: $DOCKER_SOCK"
fi

uv run memsearch graph-watchdog \
  --execute \
  --state-path "$STATE_DIR/watchdog.json" \
  --json-output
```

Adjust flags to match the final `graph-watchdog` command. Keep the script Mini-specific and do not source secrets unless the command needs them.

- [ ] **Step 4: Render watchdog plist**

Modify `src/memsearch/backfill/scheduler.py` to add Graphiti Mini plists only when the `machine` argument identifies Dominic's Mac mini. Existing MacBook source-sync plists must keep rendering as they do today.

For the watchdog plist, add:

- label `com.monkhouse.graphiti-mon316-watchdog`;
- `ProgramArguments` pointing at `bin/graphiti-watchdog-mon316.sh`;
- `RunAtLoad: True`;
- `StartInterval: 300`;
- stdout/stderr under `.local/source-sync-logs/` or SSD logs, but keep one canonical log in `/Volumes/SSD/graphiti-mon316/logs/watchdog.log`.

- [ ] **Step 5: Run scheduler tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_scheduler.py tests/backfill_chats/test_graphiti_scheduler.py -q
```

Expected: existing Linear/Manus scheduler tests still pass and watchdog test passes.

- [ ] **Step 6: Render locally and inspect**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents --machine "Dominic's Mac mini"
plutil -p .local/launchagents/com.monkhouse.graphiti-mon316-watchdog.plist
```

Expected: plist renders but is not installed. `.local/launchagents` remains ignored.

- [ ] **Step 7: Full gate**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_scheduler.py tests/backfill_chats/test_graphiti_scheduler.py tests/test_graphiti_watchdog.py -q
uv run ruff check src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add bin/graphiti-watchdog-mon316.sh src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py
git commit -m "MON-348 render graphiti watchdog launchagent"
```

Expected: commit references the Linear issue.

## Task 5: Source Freshness Proof Job

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/bin/graphiti-source-freshness-proof-mon316.sh`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/tests/backfill_chats/test_graphiti_scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/source-freshness-automation.md`

- [ ] **Step 1: Extend scheduler test**

Add to `tests/backfill_chats/test_graphiti_scheduler.py`:

```python
def test_scheduler_renders_source_freshness_proof(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.memsearch.source-freshness-proof" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.source-freshness-proof.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Hour": 6, "Minute": 45}
    assert "graphiti-source-freshness-proof-mon316.sh" in " ".join(payload["ProgramArguments"])
```

- [ ] **Step 2: Run failing test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_graphiti_scheduler.py -q
```

Expected: fails because the proof plist is not rendered.

- [ ] **Step 3: Create proof wrapper**

Create `bin/graphiti-source-freshness-proof-mon316.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/source-freshness-proof.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] source freshness proof start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] warning: /Users/dominicmonkhouse/.secrets/mcp.env not found"
fi

uv run python -m memsearch.backfill.cli source-freshness --run-proof
```

- [ ] **Step 4: Render proof plist**

Modify `src/memsearch/backfill/scheduler.py` to render `com.memsearch.source-freshness-proof.plist` at 06:45 daily only for Dominic's Mac mini. Do not render this SSD-logging job on the MacBook.

Expected ordering: Linear sync at 06:30, proof at 06:45.

- [ ] **Step 5: Update docs**

Add a `Daily proof job` section to `docs/source-freshness-automation.md`:

```markdown
## Daily proof job

After the 06:30 Linear sync, `com.memsearch.source-freshness-proof` runs at 06:45 and executes:

```bash
uv run python -m memsearch.backfill.cli source-freshness --run-proof
```

The job writes logs to `/Volumes/SSD/graphiti-mon316/logs/source-freshness-proof.log` on the Mini.
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_scheduler.py tests/backfill_chats/test_graphiti_scheduler.py -q
uv run ruff check src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add bin/graphiti-source-freshness-proof-mon316.sh src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py docs/source-freshness-automation.md
git commit -m "MON-348 add memsearch source freshness proof job"
```

Expected: commit references the Linear issue.

## Task 6: Graphiti Candidate Report

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/graphiti/candidates.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_candidates.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_cli.py`

- [ ] **Step 1: Write failing candidate tests**

Create `tests/test_graphiti_candidates.py`:

```python
from __future__ import annotations

from pathlib import Path

from memsearch.graphiti.candidates import CandidateStatus, build_candidate_report


def test_candidate_report_rejects_raw_memory_and_stale_routes(tmp_path):
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-12.md"
    stale_seed = tmp_path / "docs" / "graphiti-curated-seeds" / "stale-route.md"
    raw.parent.mkdir(parents=True)
    stale_seed.parent.mkdir(parents=True)
    raw.write_text("### Old route\n\nUse the historical raw memory export.\n", encoding="utf-8")
    stale_seed.write_text(
        "### Old route\n\nClassification: current\n\nUse .nord hostnames and restart Meshnet.\n\nEvidence: docs/graphiti-falkordb.md\n",
        encoding="utf-8",
    )

    report = build_candidate_report([raw, stale_seed])

    assert report.accepted == []
    assert report.rejected[0].status == CandidateStatus.REJECTED_RAW_SOURCE
    assert any(item.status == CandidateStatus.REJECTED_STALE_ROUTE for item in report.rejected)


def test_candidate_report_accepts_evidence_cited_seed(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "capped-batch-999.md"
    seed.parent.mkdir(parents=True)
    seed.write_text(
        "### Current route\n\nClassification: current\n\nGraphiti MCP is served through Tailscale Serve on port 8018.\n\nEvidence: docs/graphiti-falkordb.md\n",
        encoding="utf-8",
    )

    report = build_candidate_report([seed])

    assert len(report.accepted) == 1
    assert report.accepted[0].source == seed
    assert report.accepted[0].classification == "current"


def test_candidate_report_requires_classification(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "missing-classification.md"
    seed.parent.mkdir(parents=True)
    seed.write_text("### Route\n\nGraphiti uses Tailscale Serve.\n\nEvidence: docs/graphiti-falkordb.md\n", encoding="utf-8")

    report = build_candidate_report([seed])

    assert report.accepted == []
    assert report.rejected[0].status == CandidateStatus.REJECTED_MISSING_CLASSIFICATION
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_candidates.py -q
```

Expected: fails because `candidates.py` does not exist.

- [ ] **Step 3: Implement candidate model**

Create `src/memsearch/graphiti/candidates.py` with:

- `CandidateStatus` enum.
- `CandidateItem` dataclass.
- `CandidateReport` dataclass.
- `build_candidate_report(paths: Iterable[Path]) -> CandidateReport`.
- hard rejections for raw sessions, raw Manus exports, `.memsearch/memory` daily files, stale route tokens, and files without evidence markers.
- required classification for every accepted statement: `current`, `historical`, `superseded`, or `unsafe`.
- automatic rejection from ingest-ready output for anything except `current`.
- no semantic judgement beyond the explicit `Classification:` marker and deterministic safety checks. The report lists candidates for human review; it does not decide truth.

Minimum stale tokens:

```python
STALE_ROUTE_TOKENS = (".nord", "Meshnet", "100.87.225.99", "restart NordVPN", "restart Meshnet")
```

Important: a token can be allowed only if the statement explicitly labels it stale or historical. Keep the first version conservative.

Classification rules:

- `current`: eligible for accepted candidates if evidence is present and no stale token risk remains.
- `historical`: include in the report for context, but never in ingest-ready seed output.
- `superseded`: include in rejected/superseded section, never accepted.
- `unsafe`: include in rejected section with reason.
- missing classification: reject with `REJECTED_MISSING_CLASSIFICATION`.

Keep this first version deliberately small. Do not add scoring, summarisation, or automatic rewriting. The output is a review queue: accepted means "eligible for human review as a seed", not "automatically true".

- [ ] **Step 4: Add CLI command**

Add `graph-candidate-report` to `src/memsearch/cli.py`:

```bash
memsearch graph-candidate-report docs/graphiti-curated-seeds /Users/dominicmonkhouse/Projects/claude-config/memory --output outputs/YYYY-MM-DD/graphiti-candidates.md
```

Behaviour:

- no Graphiti mutation;
- writes a human-readable report;
- exits non-zero if accepted candidates lack evidence;
- exits non-zero if any accepted candidate lacks `Classification: current`;
- includes accepted, rejected, and needs-review sections;
- includes current-state classification for every candidate statement;
- includes exact source paths.

- [ ] **Step 5: Add CLI tests**

Add to `tests/test_graphiti_cli.py`:

```python
def test_graph_candidate_report_writes_report(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "seed.md"
    output = tmp_path / "report.md"
    seed.parent.mkdir(parents=True)
    seed.write_text("### Current\n\nClassification: current\n\nGraphiti uses FalkorDB.\n\nEvidence: docs/graphiti-falkordb.md\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["graph-candidate-report", str(seed), "--output", str(output)])

    assert result.exit_code == 0
    assert output.is_file()
    body = output.read_text()
    assert "Accepted" in body
    assert "Classification: current" in body
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_candidates.py tests/test_graphiti_cli.py -q
uv run ruff check src/memsearch/graphiti/candidates.py src/memsearch/cli.py tests/test_graphiti_candidates.py tests/test_graphiti_cli.py
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add src/memsearch/graphiti/candidates.py src/memsearch/cli.py tests/test_graphiti_candidates.py tests/test_graphiti_cli.py
git commit -m "MON-348 add graphiti candidate report"
```

Expected: no unrelated files staged.

## Task 7: Candidate Report Wrapper and Scheduler

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/bin/graphiti-candidate-report-mon316.sh`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/tests/backfill_chats/test_graphiti_scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-falkordb.md`

- [ ] **Step 1: Extend scheduler test**

Add to `tests/backfill_chats/test_graphiti_scheduler.py`:

```python
def test_scheduler_renders_graphiti_candidate_report(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.memsearch.graphiti-candidate-report" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.graphiti-candidate-report.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Weekday": 1, "Hour": 7, "Minute": 0}
    assert "graphiti-candidate-report-mon316.sh" in " ".join(payload["ProgramArguments"])
```

- [ ] **Step 2: Run failing test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_graphiti_scheduler.py -q
```

Expected: fails because the candidate report plist is not rendered.

- [ ] **Step 3: Create wrapper**

Create `bin/graphiti-candidate-report-mon316.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
TODAY="$(date '+%Y-%m-%d')"
OUTPUT_DIR="$REPO_ROOT/outputs/$TODAY"
CURATED_SEEDS_DIR="${CURATED_SEEDS_DIR:-$REPO_ROOT/docs/graphiti-curated-seeds}"
CLAUDE_MEMORY_DIR="${CLAUDE_MEMORY_DIR:-/Users/dominicmonkhouse/Projects/claude-config/memory}"
LINEAR_MEMORY_DIR="${LINEAR_MEMORY_DIR:-/Users/dominicmonkhouse/Projects/.memsearch/memory/linear}"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/candidate-report.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti candidate report start"

uv run memsearch graph-candidate-report \
  "$CURATED_SEEDS_DIR" \
  "$CLAUDE_MEMORY_DIR" \
  "$LINEAR_MEMORY_DIR" \
  --output "$OUTPUT_DIR/graphiti-candidate-report.md"
```

This job must not call `graph-index-curated`.

- [ ] **Step 4: Render scheduler**

Modify scheduler to render `com.memsearch.graphiti-candidate-report.plist` weekly Monday 07:00, after Manus weekly sync at 06:00, only for Dominic's Mac mini.

- [ ] **Step 5: Update docs**

Add to `docs/graphiti-falkordb.md`:

```markdown
## Curated freshness workflow

Graphiti freshness is candidate-first. The weekly candidate job writes a report under `outputs/YYYY-MM-DD/` and does not mutate Graphiti. Approved batches are ingested manually with `graph-index-curated --dry-run` followed by a capped real run.
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/backfill_chats/test_scheduler.py tests/backfill_chats/test_graphiti_scheduler.py tests/test_graphiti_candidates.py -q
uv run ruff check src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add bin/graphiti-candidate-report-mon316.sh src/memsearch/backfill/scheduler.py tests/backfill_chats/test_graphiti_scheduler.py docs/graphiti-falkordb.md
git commit -m "MON-348 schedule graphiti candidate reports"
```

Expected: no unrelated files staged.

## Task 8: Capped Ingest Runbook and Guardrail Tests

**Files:**
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-falkordb.md`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/source-freshness-automation.md`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_cli.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`

- [ ] **Step 1: Add test for uncapped refusal remains intact**

Confirm existing `test_graph_index_curated_requires_real_run_cap` remains present. Add a test for broad raw source refusal if missing:

```python
def test_graph_index_curated_dry_run_excludes_raw_daily_memory(monkeypatch, tmp_path):
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-14.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("### Raw\n\nTroubleshooting notes.\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(cli, ["graph-index-curated", str(tmp_path / ".memsearch" / "memory"), "--dry-run"])

    assert result.exit_code == 0
    assert "0 selected" in result.output
```

- [ ] **Step 2: Run focused test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_cli.py::test_graph_index_curated_requires_real_run_cap tests/test_graphiti_cli.py::test_graph_index_curated_dry_run_excludes_raw_daily_memory -q
```

Expected: pass.

- [ ] **Step 3: Add guarded clear-group CLI for rollback**

Add `graph-clear-group` to `src/memsearch/cli.py`.

Requirements:

- requires `--group-id`;
- refuses to run unless `--confirm-group-id` exactly matches `--group-id`;
- defaults to dry-run unless `--execute` is passed;
- prints the endpoint and group ID before executing;
- calls `GraphitiClient.clear_graph(group_id=group_id)` only in execute mode;
- must not accept broad values such as `all`, `*`, or empty strings.

Add tests to `tests/test_graphiti_cli.py`:

```python
def test_graph_clear_group_requires_matching_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(
        cli,
        ["graph-clear-group", "--group-id", "ms_memsearch_active_curated_v1", "--confirm-group-id", "wrong", "--execute"],
    )

    assert result.exit_code == 1
    assert "confirmation" in result.output.lower()


def test_graph_clear_group_execute_calls_client(monkeypatch, tmp_path):
    calls = []

    class ClearClient(FakeGraphitiClient):
        def clear_graph(self, *, group_id):
            calls.append(group_id)
            return {"message": "cleared"}

    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", ClearClient)

    result = CliRunner().invoke(
        cli,
        [
            "graph-clear-group",
            "--group-id",
            "ms_memsearch_active_curated_v1",
            "--confirm-group-id",
            "ms_memsearch_active_curated_v1",
            "--execute",
        ],
    )

    assert result.exit_code == 0
    assert calls == ["ms_memsearch_active_curated_v1"]
```

- [ ] **Step 4: Run clear-group tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_cli.py::test_graph_clear_group_requires_matching_confirmation tests/test_graphiti_cli.py::test_graph_clear_group_execute_calls_client -q
```

Expected: pass.

- [ ] **Step 5: Document approved ingest runbook**

Add to `docs/graphiti-falkordb.md`:

```markdown
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
```

- [ ] **Step 6: Document rollback**

Add rollback steps:

- save failing graph-search output;
- clear only `ms_memsearch_active_curated_v1` with the guarded command:

```bash
uv run memsearch graph-clear-group \
  --group-id ms_memsearch_active_curated_v1 \
  --confirm-group-id ms_memsearch_active_curated_v1 \
  --execute
```

- restore manifest checkpoint;
- rebuild from known-good seed files only;
- re-run graph-eval;
- never run `docker compose down -v`.

- [ ] **Step 7: Run docs and tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_cli.py tests/test_graphiti_curated.py -q
uv run ruff check src/memsearch/cli.py tests/test_graphiti_cli.py
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add docs/graphiti-falkordb.md docs/source-freshness-automation.md src/memsearch/cli.py tests/test_graphiti_cli.py
git commit -m "MON-348 document capped graphiti ingest runbook"
```

Expected: no unrelated files staged.

## Task 9: Persistence Backup and Restore Drill

**Files:**
- Create: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/graphiti/backup.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/tests/test_graphiti_backup.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/cli.py`
- Create: `/Users/dominicmonkhouse/Projects/memsearch/bin/graphiti-backup-mon316.sh`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/tests/backfill_chats/test_graphiti_scheduler.py`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-falkordb.md`

- [ ] **Step 1: Write backup path tests**

Create `tests/test_graphiti_backup.py`:

```python
from __future__ import annotations

from pathlib import Path

from memsearch.graphiti.backup import backup_path_for_timestamp


def test_backup_path_stays_under_graphiti_ssd_root():
    path = backup_path_for_timestamp(Path("/Volumes/SSD/graphiti-mon316/backups"), "20260614-120000")

    assert path == Path("/Volumes/SSD/graphiti-mon316/backups/20260614-120000")


def test_backup_path_rejects_traversal():
    try:
        backup_path_for_timestamp(Path("/Volumes/SSD/graphiti-mon316/backups"), "../bad")
    except ValueError as exc:
        assert "invalid backup timestamp" in str(exc)
    else:
        raise AssertionError("expected invalid timestamp rejection")
```

- [ ] **Step 2: Run failing test**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_backup.py -q
```

Expected: fails because module does not exist.

- [ ] **Step 3: Implement backup helpers**

Create `src/memsearch/graphiti/backup.py` with pure helper functions first:

```python
from __future__ import annotations

from pathlib import Path


def backup_path_for_timestamp(root: Path, timestamp: str) -> Path:
    if "/" in timestamp or ".." in timestamp:
        raise ValueError("invalid backup timestamp")
    return root / timestamp
```

Do not implement destructive restore in code. Keep restore drill documented and manual/approval-gated.

- [ ] **Step 4: Add CLI backup command**

Add `graph-backup` command that defaults to dry-run and executes only with `--execute`.

Dry-run output must print:

- Docker volume name;
- expected FalkorDB container data path;
- backup destination;
- exact non-destructive commands to run;
- no `down -v`.

Execute mode must:

- create a dated backup directory under `/Volumes/SSD/graphiti-mon316/backups`;
- save a metadata JSON file with timestamp, volume name, container names, and command versions;
- produce a database-level consistent snapshot before copying data. Preferred sequence:
  1. run `redis-cli BGSAVE` or the FalkorDB container's equivalent snapshot command inside the FalkorDB container;
  2. poll persistence status until the save completes or a bounded timeout is reached;
  3. copy the resulting `/var/lib/falkordb/data` snapshot files into the dated backup directory;
  4. fail closed if the container does not expose a snapshot command. Do not live-copy an active data directory as a fallback.
- copy or export FalkorDB data without removing containers or volumes;
- print the backup path at the end;
- fail if the backup path is outside `/Volumes/SSD/graphiti-mon316/backups`.
- support `--retain-days 30` and `--prune-to-trash`, moving old dated backup directories to `~/.Trash/graphiti-mon316-backups/` only after a new backup succeeds. The scheduled job should use this safe-delete mode. It must never use `rm -rf`.

- [ ] **Step 5: Test CLI dry run**

Add CLI tests confirming:

- `graphiti_mon316_falkordb_data`;
- `/var/lib/falkordb/data`;
- does not include `down -v`.
- `--execute` calls the backup runner and returns the artefact path.

- [ ] **Step 6: Add nightly backup wrapper**

Create `bin/graphiti-backup-mon316.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
BACKUP_ROOT="/Volumes/SSD/graphiti-mon316/backups"
COLIMA_PROFILE="graphiti-mon316"
COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"
DOCKER_SOCK="$COLIMA_HOME/$COLIMA_PROFILE/docker.sock"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$BACKUP_ROOT"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/backup.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti backup start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
fi

if [ -S "$DOCKER_SOCK" ]; then
  export DOCKER_HOST="unix://$DOCKER_SOCK"
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] dedicated Docker socket missing: $DOCKER_SOCK"
  exit 1
fi

uv run memsearch graph-backup --execute --backup-root "$BACKUP_ROOT" --retain-days 30 --prune-to-trash
```

- [ ] **Step 7: Render backup scheduler**

Extend `tests/backfill_chats/test_graphiti_scheduler.py`:

```python
def test_scheduler_renders_graphiti_backup(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-backup" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.monkhouse.graphiti-mon316-backup.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Hour": 3, "Minute": 15}
    assert "graphiti-backup-mon316.sh" in " ".join(payload["ProgramArguments"])
```

Modify `src/memsearch/backfill/scheduler.py` to render the nightly backup plist at 03:15 local time only for Dominic's Mac mini.

- [ ] **Step 8: Document restore drill**

Add to `docs/graphiti-falkordb.md`:

- backup cadence;
- backup LaunchAgent label `com.monkhouse.graphiti-mon316-backup`;
- backup artefact location `/Volumes/SSD/graphiti-mon316/backups/<timestamp>/`;
- snapshot mechanism, including the exact FalkorDB/Redis save command used before copying;
- retention policy: keep 30 days by moving older dated backup directories to `~/.Trash/graphiti-mon316-backups/` after a successful new backup;
- temporary non-production restore drill;
- explicit prohibition on production group clearing without rollback procedure;
- evidence to save after the drill.

- [ ] **Step 9: Run tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_backup.py tests/test_graphiti_cli.py tests/backfill_chats/test_graphiti_scheduler.py -q
uv run ruff check src/memsearch/graphiti/backup.py src/memsearch/cli.py src/memsearch/backfill/scheduler.py tests/test_graphiti_backup.py tests/test_graphiti_cli.py tests/backfill_chats/test_graphiti_scheduler.py
```

Expected: pass.

- [ ] **Step 10: Commit**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add src/memsearch/graphiti/backup.py src/memsearch/cli.py bin/graphiti-backup-mon316.sh src/memsearch/backfill/scheduler.py tests/test_graphiti_backup.py tests/test_graphiti_cli.py tests/backfill_chats/test_graphiti_scheduler.py docs/graphiti-falkordb.md
git commit -m "MON-348 add graphiti persistence backup job"
```

Expected: no unrelated files staged.

## Task 10: Mini Deployment and LaunchAgent Install

**Files:**
- Modify on Mini only after approval:
  - `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-watchdog.plist`
  - `~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-backup.plist`
  - `~/Library/LaunchAgents/com.memsearch.source-freshness-proof.plist`
  - `~/Library/LaunchAgents/com.memsearch.graphiti-candidate-report.plist`
- Repo files read at runtime:
  - `bin/graphiti-watchdog-mon316.sh`
  - `bin/graphiti-backup-mon316.sh`
  - `bin/graphiti-source-freshness-proof-mon316.sh`
  - `bin/graphiti-candidate-report-mon316.sh`
  - `deploy/graphiti/docker-compose.yml`
  - `deploy/graphiti/docker-compose.mini.yml`

- [ ] **Step 1: Pull code before any runtime command that reads new files**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && git pull --ff-only fork main && /Users/dominicmonkhouse/.local/bin/uv sync'
```

Expected: target has all scripts before LaunchAgents reference them.

- [ ] **Step 2: Verify scripts exist and are executable**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && ls -l bin/graphiti-watchdog-mon316.sh bin/graphiti-backup-mon316.sh bin/graphiti-source-freshness-proof-mon316.sh bin/graphiti-candidate-report-mon316.sh'
```

Expected: all scripts exist and executable bit is set. If not, fix in repo and commit before installing LaunchAgents.

- [ ] **Step 3: Apply updated Compose config to running Graphiti stack**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && bin/start-graphiti-mon316.sh'
```

Expected: Docker Compose reconciles the running Graphiti/FalkorDB services using the updated Compose file. Existing FalkorDB named volume is preserved.

- [ ] **Step 4: Verify live Docker restart policy**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"; export DOCKER_HOST="unix://$COLIMA_HOME/graphiti-mon316/docker.sock"; for c in graphiti-mon316-falkordb-1 graphiti-mon316-graphiti-mcp-1; do echo "__CONTAINER__:$c"; docker inspect "$c" --format "{{json .HostConfig.RestartPolicy}}"; done'
```

Expected: both containers show `{"Name":"unless-stopped","MaximumRetryCount":0}` or Docker's equivalent representation.

- [ ] **Step 5: Verify health after Compose reconcile**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"; export DOCKER_HOST="unix://$COLIMA_HOME/graphiti-mon316/docker.sock"; curl -fsS http://127.0.0.1:18018/health; echo; docker ps --format "{{.Names}} {{.Status}}" | grep -E "graphiti|falkor|milvus"'
```

Expected: Graphiti health OK and Milvus remains healthy.

- [ ] **Step 6: Render Mini LaunchAgents**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents --machine "Dominic'"'"'s Mac mini"'
```

Expected: summary includes Linear, Manus, watchdog, backup, source freshness proof, and candidate report plists.

- [ ] **Step 7: Inspect rendered plists**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && for f in .local/launchagents/*.plist; do echo "__FILE__:$f"; plutil -p "$f"; done'
```

Expected: paths point to `~/Projects/memsearch`, not stale worktrees, and no secrets are printed.

- [ ] **Step 8: Backup existing installed plists**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'stamp=$(date +%Y%m%d-%H%M%S); backup="$HOME/.Trash/graphiti-launchagents-backup-$stamp"; mkdir -p "$backup"; for f in ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-watchdog.plist ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-backup.plist ~/Library/LaunchAgents/com.memsearch.source-freshness-proof.plist ~/Library/LaunchAgents/com.memsearch.graphiti-candidate-report.plist; do [ -f "$f" ] && cp "$f" "$backup/"; done; echo "$backup"'
```

Expected: backup folder exists if any prior plists existed. This is copy-only, not deletion.

- [ ] **Step 9: Install plists**

Run only after explicit execution approval:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && cp .local/launchagents/com.monkhouse.graphiti-mon316-watchdog.plist ~/Library/LaunchAgents/ && cp .local/launchagents/com.monkhouse.graphiti-mon316-backup.plist ~/Library/LaunchAgents/ && cp .local/launchagents/com.memsearch.source-freshness-proof.plist ~/Library/LaunchAgents/ && cp .local/launchagents/com.memsearch.graphiti-candidate-report.plist ~/Library/LaunchAgents/'
```

Expected: files copied.

- [ ] **Step 10: Bootstrap or kickstart LaunchAgents**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'uid=$(id -u); for label in com.monkhouse.graphiti-mon316-watchdog com.monkhouse.graphiti-mon316-backup com.memsearch.source-freshness-proof com.memsearch.graphiti-candidate-report; do launchctl bootout gui/$uid ~/Library/LaunchAgents/$label.plist 2>/dev/null || true; launchctl bootstrap gui/$uid ~/Library/LaunchAgents/$label.plist; launchctl kickstart -k gui/$uid/$label; done'
```

Expected: all four load without error.

- [ ] **Step 11: Verify running state**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'uid=$(id -u); for label in com.monkhouse.graphiti-mon316-watchdog com.monkhouse.graphiti-mon316-backup com.memsearch.source-freshness-proof com.memsearch.graphiti-candidate-report; do echo "__LABEL__:$label"; launchctl print gui/$uid/$label | sed -n "1,120p"; done'
```

Expected:

- watchdog has `RunAtLoad` and interval;
- backup has 03:15 calendar trigger and last exit `0` after kickstart;
- proof and candidate jobs have calendar triggers;
- last exit is `0` after kickstart or command-specific expected status.

- [ ] **Step 12: Verify backup artefact**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'ls -lt /Volumes/SSD/graphiti-mon316/backups | head -5; find /Volumes/SSD/graphiti-mon316/backups -maxdepth 2 -type f | tail -20'
```

Expected: at least one dated backup artefact or metadata file exists after kickstart.

- [ ] **Step 13: Verify no Milvus disruption**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"; export DOCKER_HOST="unix://$COLIMA_HOME/graphiti-mon316/docker.sock"; docker ps --format "{{.Names}} {{.Status}}" | grep -E "milvus|graphiti|falkor"'
```

Expected: Milvus and Graphiti/FalkorDB remain healthy.

- [ ] **Step 14: Update Linear**

Add a Linear comment with:

- installed labels;
- health output summary;
- log paths;
- any skipped job and why.

Expected: Linear issue remains the execution control surface.

## Task 11: First Candidate and Capped Ingest Pilot

**Files:**
- Create after approval: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-curated-seeds/capped-batch-009.md`
- Create after approval: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-curated-seeds/capped-batch-009-sources.md`
- Runtime state: `.memsearch/graphiti-curated-manifest.json` on Mini, ignored by git.

- [ ] **Step 1: Generate candidate report**

Run on Mini:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && bin/graphiti-candidate-report-mon316.sh && ls -lt outputs/$(date +%Y-%m-%d)/graphiti-candidate-report.md'
```

Expected: report exists and Graphiti was not mutated.

- [ ] **Step 2: Review accepted candidates**

Read the report. Pick at most 10 current, evidence-backed relationship facts. Reject anything with ambiguous current-state wording.

Expected: a short list of proposed seed statements.

- [ ] **Step 3: Create seed and source files**

Create `docs/graphiti-curated-seeds/capped-batch-009.md` with one extraction-friendly relationship per line.

Create `docs/graphiti-curated-seeds/capped-batch-009-sources.md` mapping every statement to source path and line or Linear evidence.

- [ ] **Step 4: Run tests**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_graphiti_cli.py tests/test_graphiti_curated.py tests/test_graphiti_candidates.py -q
uv run ruff check docs/graphiti-curated-seeds src/memsearch tests
```

Expected: pass.

- [ ] **Step 5: Commit seed files**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add docs/graphiti-curated-seeds/capped-batch-009.md docs/graphiti-curated-seeds/capped-batch-009-sources.md
git commit -m "MON-348 add graphiti capped batch 009 seeds"
```

Expected: only seed/source files staged.

- [ ] **Step 6: Deploy seed files to Mini**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && git pull --ff-only fork main'
```

Expected: seed files exist on Mini before ingestion commands read them.

- [ ] **Step 7: Baseline graph evaluation**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-status && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-eval --json-output'
```

Expected: graph status OK and evaluation pass before ingest.

- [ ] **Step 8: Checkpoint manifest**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && mkdir -p .memsearch/manifest-checkpoints && cp .memsearch/graphiti-curated-manifest.json .memsearch/manifest-checkpoints/graphiti-curated-manifest-before-batch-009-$(date +%Y%m%d-%H%M%S).json'
```

Expected: checkpoint exists.

- [ ] **Step 9: Dry-run capped ingest**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-index-curated docs/graphiti-curated-seeds/capped-batch-009.md --dry-run'
```

Expected: exact selected, excluded, episode, and pending counts match the approved batch.

- [ ] **Step 10: Run capped ingest**

Run only after explicit approval for this batch:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-index-curated docs/graphiti-curated-seeds/capped-batch-009.md --limit 10'
```

Expected: queued count matches approved pending count, or less if unchanged.

- [ ] **Step 11: Evaluate and probe**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-eval --json-output && /Users/dominicmonkhouse/.local/bin/uv run memsearch search "Is NordVPN still used or is this Tailscale only?" --include-graph --top-k 5 --json-output'
```

Expected: evaluation passes and negative control does not recommend NordVPN, Meshnet, `.nord`, or stale IPs.

- [ ] **Step 12: Rollback if needed**

If evaluation fails, do not continue. Run the documented rollback from `docs/graphiti-falkordb.md`, using:

```bash
uv run memsearch graph-clear-group \
  --group-id ms_memsearch_active_curated_v1 \
  --confirm-group-id ms_memsearch_active_curated_v1 \
  --execute
```

Then restore the checkpoint, rebuild known-good seeds, re-run `graph-eval`, and record the rejected batch in Linear.

## Task 12: Documentation Closeout

**Files:**
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/graphiti-falkordb.md`
- Modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/source-freshness-automation.md`
- Optional modify: `/Users/dominicmonkhouse/Projects/memsearch/docs/cli.md`

- [ ] **Step 1: Update operations overview**

Ensure docs state:

- Graphiti is user-session supervised, not reboot-without-login guaranteed.
- Runtime watchdog, backup, and source proof jobs are installed on Mini.
- Candidate report is non-mutating.
- Capped ingest is approval-gated.
- FalkorDB backup/restore drill is non-destructive.

- [ ] **Step 2: Update CLI docs if commands were added**

If new CLI commands exist, add concise entries to `docs/cli.md`:

- `memsearch graph-watchdog`
- `memsearch graph-candidate-report`
- `memsearch graph-backup`

- [ ] **Step 3: Run docs-relevant checks**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest tests/test_cli_help.py tests/test_graphiti_cli.py tests/backfill_chats/test_scheduler.py tests/backfill_chats/test_graphiti_scheduler.py -q
uv run ruff check src tests
```

Expected: pass.

- [ ] **Step 4: Commit docs**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
git add docs/graphiti-falkordb.md docs/source-freshness-automation.md docs/cli.md
git commit -m "MON-348 document graphiti freshness operations"
```

Expected: commit references the Linear issue.

## Task 13: Final Verification and Linear Closeout

**Files:**
- No repo edits unless verification finds documentation drift.

- [ ] **Step 1: Run full local verification**

Run:

```bash
cd /Users/dominicmonkhouse/Projects/memsearch
uv run pytest -q
uv run ruff check src tests
```

Expected: full test and lint gates pass.

- [ ] **Step 2: Verify Mini running process**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'COLIMA_HOME="${COLIMA_HOME:-$HOME/.colima}"; export DOCKER_HOST="unix://$COLIMA_HOME/graphiti-mon316/docker.sock"; curl -fsS http://127.0.0.1:18018/health; echo; tailscale serve status --json; docker ps --format "{{.Names}} {{.Status}}" | grep -E "graphiti|falkor|milvus"'
```

Expected: Graphiti health OK, Tailscale Serve TCP forward present, Graphiti/FalkorDB/Milvus healthy.

- [ ] **Step 3: Verify LaunchAgents**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'uid=$(id -u); for label in com.monkhouse.graphiti-mon316 com.monkhouse.graphiti-mon316-awake com.monkhouse.graphiti-mon316-watchdog com.memsearch.daily-linear-sync com.memsearch.weekly-manus-sync com.memsearch.source-freshness-proof com.memsearch.graphiti-candidate-report; do echo "__LABEL__:$label"; launchctl print gui/$uid/$label | grep -E "state =|last exit code|run interval|StartCalendarInterval|properties" || true; done'
```

Expected: existing and new agents are loaded; watchdog/proof/report jobs show healthy last exit after test kickstart or expected scheduled state.

- [ ] **Step 4: Verify graph CLI on Mini**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-status && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-eval --json-output'
```

Expected: status OK and graph evaluation passes.

- [ ] **Step 5: Verify vector freshness**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run python -m memsearch.backfill.cli source-freshness --run-proof'
```

Expected: Linear proof passes; Manus proof is either current or clearly waiting for weekly run.

- [ ] **Step 6: Verify candidate report is non-mutating**

Run candidate report, then compare manifest mtime/count before and after:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && before=$(stat -f "%m" .memsearch/graphiti-curated-manifest.json 2>/dev/null || echo missing); bin/graphiti-candidate-report-mon316.sh; after=$(stat -f "%m" .memsearch/graphiti-curated-manifest.json 2>/dev/null || echo missing); echo "before=$before after=$after"'
```

Expected: manifest mtime unchanged.

- [ ] **Step 7: Update Linear**

Re-read the Linear issue. Move it to Done only if:

- repo changes are committed and pushed if required;
- Mini runtime is verified;
- LaunchAgents are loaded;
- docs are updated;
- no graph evaluation failure remains.

If anything remains, leave the issue open and comment with the blocker.

## Rollback Plan

Runtime rollback:

1. Boot out only newly added LaunchAgents:

```bash
ssh dom-kamet.tailf78a36.ts.net 'uid=$(id -u); for label in com.monkhouse.graphiti-mon316-watchdog com.monkhouse.graphiti-mon316-backup com.memsearch.source-freshness-proof com.memsearch.graphiti-candidate-report; do launchctl bootout gui/$uid ~/Library/LaunchAgents/$label.plist 2>/dev/null || true; done'
```

2. Move newly installed plists to Trash only after listing them and confirming they are the new plists:

```bash
ssh dom-kamet.tailf78a36.ts.net 'for f in ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-watchdog.plist ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-backup.plist ~/Library/LaunchAgents/com.memsearch.source-freshness-proof.plist ~/Library/LaunchAgents/com.memsearch.graphiti-candidate-report.plist; do [ -f "$f" ] && ls -l "$f"; done'
```

Then, only with explicit approval:

```bash
ssh dom-kamet.tailf78a36.ts.net 'for f in ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-watchdog.plist ~/Library/LaunchAgents/com.monkhouse.graphiti-mon316-backup.plist ~/Library/LaunchAgents/com.memsearch.source-freshness-proof.plist ~/Library/LaunchAgents/com.memsearch.graphiti-candidate-report.plist; do [ -f "$f" ] && mv "$f" ~/.Trash/; done'
```

3. Re-run existing Graphiti start guard:

```bash
ssh dom-kamet.tailf78a36.ts.net '~/Projects/memsearch/bin/start-graphiti-mon316.sh'
```

Graph rollback:

1. Save failing outputs.
2. Clear only `ms_memsearch_active_curated_v1`:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd ~/Projects/memsearch && /Users/dominicmonkhouse/.local/bin/uv run memsearch graph-clear-group --group-id ms_memsearch_active_curated_v1 --confirm-group-id ms_memsearch_active_curated_v1 --execute'
```

3. Restore `.memsearch/graphiti-curated-manifest.json` from the pre-batch checkpoint.
4. Rebuild known-good seed files only.
5. Run `graph-eval --json-output`.
6. Record rejected batch in Linear.

Repo rollback:

- Use normal git revert commits for committed code if needed.
- Do not use `git reset --hard`.

## Review Status

- Plan-document reviewer: approved on third pass at 2026-06-14T19:42:12+0100.
- Cross-model adversarial review: completed at 2026-06-14T19:52:35+0100; blockers folded into this plan.
- AP check: CLEAN PASS on attempt 2 at 2026-06-14T20:21:07+0100.
- Linear handoff: MON-348 — https://linear.app/monkhouseandcompany/issue/MON-348/graphiti-memsearch-keepalive-freshness-automation-implementation-plan

## Plan-document review fixes

- Added Linear tracking as an implementation prerequisite before Task 1 and replaced commit placeholders with `MON-348`.
- Strengthened Task 3 so `graph-watchdog` must perform real checks and support `--execute`; tests must prove dry-run does not execute and execute mode runs recovery.
- Strengthened Task 6 so every accepted candidate requires `Classification: current`, and every candidate statement is classified as `current`, `historical`, `superseded`, or `unsafe`.
- Expanded Task 9 from a dry-run/runbook-only backup plan into a nightly `graphiti-backup-mon316.sh` job, scheduler plist, backup artefact verification, and restore-drill documentation.
- Expanded Task 10 so deployment applies the updated Docker Compose config to the live Mini stack and verifies each container's Docker `RestartPolicy`.
- Fixed the LaunchAgent backup command to compute the timestamp once and include the backup plist in install, verification, and rollback.
- Fixed second-review issues by making the scheduled watchdog wrapper run with `--execute` and adding a guarded `graph-clear-group` CLI plus exact rollback command.

## Cross-model review fixes

- Made `pyyaml` an explicit dev/test dependency in Task 2 instead of relying on an undeclared transitive import.
- Added concrete `collect_checks()` and `run_recovery_commands()` helpers to the watchdog task so CLI tests patch real functions.
- Added a dedicated `graphiti-mon316` Colima profile check and Docker socket handling to the watchdog wrapper.
- Added consecutive-failure state and an `alert_required` flag after three failures, while deferring outbound alert destinations.
- Added Mini-only scheduler requirements and a negative MacBook scheduler test for the Graphiti Mini jobs.
- Changed the guarded rollback CLI test to assert against Click's combined `result.output`.
- Kept candidate classification, but narrowed it to explicit labels and deterministic safety checks; the report remains a human review queue, not automatic judgement.
- Made candidate report source paths overrideable through environment variables.
- Added a snapshot-first FalkorDB backup mechanism, safe Trash-based retention, and dedicated Docker socket setup for backup execution.
- Added SSD-missing fallback logging/state for the watchdog so the health monitor can still leave evidence when the SSD is unavailable.

## AP check fixes

- Accepted attempt 1 objection that Task 10 and Task 13 used bare Mini `docker inspect`/`docker ps` verification commands despite the runtime using the dedicated `graphiti-mon316` Colima socket. Added `DOCKER_HOST=unix://$COLIMA_HOME/graphiti-mon316/docker.sock` setup to every SSH Docker verification command.
- Accepted attempt 1 objection that `graphiti-source-freshness-proof-mon316.sh` sourced `/Users/dominicmonkhouse/.secrets/mcp.env` without an existence guard. Added the same guarded source pattern used by the watchdog and backup wrappers.
