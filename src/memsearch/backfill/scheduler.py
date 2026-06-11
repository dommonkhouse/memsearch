from __future__ import annotations

import json
import plistlib
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

    rendered = [
        _write_plist(
            output / "com.memsearch.daily-linear-sync.plist",
            label="com.memsearch.daily-linear-sync",
            repo_root=repo_root,
            args=[
                uv_path,
                "run",
                "python",
                "-m",
                "memsearch.backfill.cli",
                "source-sync",
                "linear",
                "--machine",
                machine,
            ],
            calendar={"Hour": 6, "Minute": 30},
            log_dir=log_dir,
        ),
        _write_plist(
            output / "com.memsearch.weekly-manus-sync.plist",
            label="com.memsearch.weekly-manus-sync",
            repo_root=repo_root,
            args=[
                uv_path,
                "run",
                "python",
                "-m",
                "memsearch.backfill.cli",
                "source-sync",
                "manus",
                "--machine",
                machine,
            ],
            calendar={"Weekday": 1, "Hour": 6, "Minute": 0},
            log_dir=log_dir,
        ),
    ]
    summary = {
        "installed": False,
        "approval_required_before_install": True,
        "plists": [item.__dict__ for item in rendered],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _write_plist(
    path: Path,
    *,
    label: str,
    repo_root: Path,
    args: list[str],
    calendar: dict[str, int],
    log_dir: Path,
) -> RenderedPlist:
    payload = {
        "Label": label,
        "ProgramArguments": args,
        "WorkingDirectory": str(repo_root),
        "StartCalendarInterval": calendar,
        "StandardOutPath": str(log_dir / f"{label}.out.log"),
        "StandardErrorPath": str(log_dir / f"{label}.err.log"),
        "RunAtLoad": False,
    }
    with path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
    return RenderedPlist(label=label, path=str(path))
