"""Graphiti runtime health checks and narrow recovery actions."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


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
TAILNET_HEALTH_HOST = "dom-kamet.tailf78a36.ts.net"
FORBIDDEN_RECOVERY_TOKENS = ("milvus", "down -v", "docker volume rm")


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


def collect_checks() -> list[WatchdogCheck]:
    docker_host = _graphiti_docker_host()
    return [
        _http_check("local_health", "http://127.0.0.1:18018/health"),
        _tailnet_health_check(),
        _command_check("colima_graphiti_mon316", ["colima", "status", "graphiti-mon316"]),
        _docker_compose_check(docker_host),
        _tailscale_serve_check(),
        _ssd_space_check(Path("/Volumes/SSD")),
    ]


def run_recovery_commands(commands: tuple[str, ...] | list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for command in commands:
        _validate_recovery_command(command)
        completed = subprocess.run(
            shlex.split(command),
            capture_output=True,
            check=False,
            text=True,
            timeout=300,
        )
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results


def checks_to_dicts(checks: list[WatchdogCheck]) -> list[dict[str, object]]:
    return [asdict(check) for check in checks]


def decision_to_dict(decision: WatchdogDecision) -> dict[str, object]:
    return asdict(decision)


def _validate_recovery_command(command: str) -> None:
    if not command.strip():
        raise ValueError("refusing empty recovery command")
    lowered = command.lower()
    for token in FORBIDDEN_RECOVERY_TOKENS:
        if token in lowered:
            raise ValueError(f"refusing recovery command containing {token!r}")
    if command not in {START_SCRIPT, TAILSCALE_REPAIR_COMMAND}:
        raise ValueError(f"refusing unknown recovery command: {command}")


def _http_check(name: str, url: str) -> WatchdogCheck:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read(500).decode("utf-8", errors="replace")
        ok = 200 <= response.status < 300
        return WatchdogCheck(name, ok, f"http {response.status}: {body}")
    except (OSError, urllib.error.URLError) as exc:
        return WatchdogCheck(name, False, str(exc))


def _tailnet_health_check() -> WatchdogCheck:
    try:
        socket.getaddrinfo(TAILNET_HEALTH_HOST, 8018)
    except OSError as exc:
        return WatchdogCheck("tailnet_health", True, f"skipped: DNS unresolved: {exc}")
    return _http_check("tailnet_health", f"http://{TAILNET_HEALTH_HOST}:8018/health")


def _command_check(name: str, command: list[str]) -> WatchdogCheck:
    try:
        completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return WatchdogCheck(name, False, str(exc))
    output = (completed.stdout or completed.stderr).strip()
    return WatchdogCheck(name, completed.returncode == 0, output or f"exit {completed.returncode}")


def _docker_compose_check(docker_host: str) -> WatchdogCheck:
    env = {**os.environ, "DOCKER_HOST": docker_host}
    command = ["docker", "compose", "-p", "graphiti-mon316", "ps", "--format", "json"]
    try:
        completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=30, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return WatchdogCheck("compose", False, str(exc))
    if completed.returncode != 0:
        return WatchdogCheck("compose", False, (completed.stderr or completed.stdout).strip())
    names = completed.stdout.lower()
    ok = "graphiti" in names and "falkor" in names
    return WatchdogCheck("compose", ok, completed.stdout.strip() or "no compose services reported")


def _tailscale_serve_check() -> WatchdogCheck:
    try:
        completed = subprocess.run(
            ["tailscale", "serve", "status", "--json"],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return WatchdogCheck("tailscale_serve", False, str(exc))
    if completed.returncode != 0:
        return WatchdogCheck("tailscale_serve", False, (completed.stderr or completed.stdout).strip())
    try:
        status = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        status = completed.stdout
    detail = json.dumps(status, sort_keys=True) if isinstance(status, dict) else str(status)
    return WatchdogCheck("tailscale_serve", "8018" in detail and "18018" in detail, detail)


def _ssd_space_check(path: Path) -> WatchdogCheck:
    if not path.exists():
        return WatchdogCheck("ssd_space", True, f"skipped: {path} missing")
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    return WatchdogCheck("ssd_space", free_gb >= 5, f"{free_gb:.1f} GB free")


def _graphiti_docker_host() -> str:
    colima_home = Path(os.environ.get("COLIMA_HOME", "/Volumes/SSD/graphiti-mon316/colima-home"))
    return f"unix://{colima_home / 'graphiti-mon316' / 'docker.sock'}"
