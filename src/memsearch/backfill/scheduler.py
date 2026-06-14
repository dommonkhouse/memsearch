from __future__ import annotations

import json
import plistlib
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RenderedPlist:
    label: str
    path: str


def render_scheduler_plists(
    *,
    output: Path,
    repo_root: Path,
    machine: str,
) -> dict[str, Any]:
    output = output.expanduser()
    output.mkdir(parents=True, exist_ok=True)
    log_dir = repo_root / ".local" / "source-sync-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    uv_path = shutil.which("uv") or "uv"
    env_path = Path.home() / ".secrets" / "mcp.env"

    rendered = [
        _write_plist(
            output / "com.memsearch.daily-linear-sync.plist",
            label="com.memsearch.daily-linear-sync",
            repo_root=repo_root,
            args=_shell_args(
                repo_root,
                env_path,
                [
                    uv_path,
                    "run",
                    "python",
                    "-m",
                    "memsearch.backfill.cli",
                    "source-sync",
                    "linear",
                    "--machine",
                    machine,
                    "--index",
                ],
            ),
            calendar={"Hour": 6, "Minute": 30},
            log_dir=log_dir,
        ),
        _write_plist(
            output / "com.memsearch.weekly-manus-sync.plist",
            label="com.memsearch.weekly-manus-sync",
            repo_root=repo_root,
            args=_shell_args(
                repo_root,
                env_path,
                [
                    uv_path,
                    "run",
                    "python",
                    "-m",
                    "memsearch.backfill.cli",
                    "source-sync",
                    "manus",
                    "--machine",
                    machine,
                    "--index",
                ],
            ),
            calendar={"Weekday": 1, "Hour": 6, "Minute": 0},
            log_dir=log_dir,
        ),
    ]
    if _is_graphiti_mini(machine):
        rendered.extend(
            [
                _write_plist(
                    output / "com.monkhouse.graphiti-mon316-watchdog.plist",
                    label="com.monkhouse.graphiti-mon316-watchdog",
                    repo_root=repo_root,
                    args=[str(repo_root / "bin" / "graphiti-watchdog-mon316.sh")],
                    interval=300,
                    log_dir=log_dir,
                    run_at_load=True,
                ),
                _write_plist(
                    output / "com.monkhouse.graphiti-mon316-backup.plist",
                    label="com.monkhouse.graphiti-mon316-backup",
                    repo_root=repo_root,
                    args=[str(repo_root / "bin" / "graphiti-backup-mon316.sh")],
                    calendar={"Hour": 3, "Minute": 15},
                    log_dir=log_dir,
                ),
                _write_plist(
                    output / "com.memsearch.source-freshness-proof.plist",
                    label="com.memsearch.source-freshness-proof",
                    repo_root=repo_root,
                    args=[str(repo_root / "bin" / "graphiti-source-freshness-proof-mon316.sh")],
                    calendar={"Hour": 6, "Minute": 45},
                    log_dir=log_dir,
                ),
                _write_plist(
                    output / "com.memsearch.graphiti-candidate-report.plist",
                    label="com.memsearch.graphiti-candidate-report",
                    repo_root=repo_root,
                    args=[str(repo_root / "bin" / "graphiti-candidate-report-mon316.sh")],
                    calendar={"Weekday": 1, "Hour": 7, "Minute": 0},
                    log_dir=log_dir,
                ),
            ]
        )
    summary = {
        "installed": False,
        "approval_required_before_install": True,
        "plists": [item.__dict__ for item in rendered],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _shell_args(repo_root: Path, env_path: Path, command: list[str]) -> list[str]:
    shell_command = " && ".join(
        [
            "set -a",
            f"source {shlex.quote(str(env_path))}",
            "set +a",
            f"cd {shlex.quote(str(repo_root))}",
            " ".join(shlex.quote(part) for part in command),
        ]
    )
    return ["/bin/zsh", "-lc", shell_command]


def _is_graphiti_mini(machine: str) -> bool:
    normalised = machine.lower()
    return "mac mini" in normalised and ("dominic" in normalised or "dom" in normalised)


def _write_plist(
    path: Path,
    *,
    label: str,
    repo_root: Path,
    args: list[str],
    calendar: dict[str, int] | None = None,
    interval: int | None = None,
    log_dir: Path,
    run_at_load: bool = False,
) -> RenderedPlist:
    payload = {
        "Label": label,
        "ProgramArguments": args,
        "WorkingDirectory": str(repo_root),
        "StandardOutPath": str(log_dir / f"{label}.out.log"),
        "StandardErrorPath": str(log_dir / f"{label}.err.log"),
        "RunAtLoad": run_at_load,
    }
    if calendar is not None:
        payload["StartCalendarInterval"] = calendar
    if interval is not None:
        payload["StartInterval"] = interval
    with path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
    return RenderedPlist(label=label, path=str(path))
