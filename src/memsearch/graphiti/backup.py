"""Non-destructive FalkorDB backup helpers for the Graphiti sidecar."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

VOLUME_NAME = "graphiti_mon316_falkordb_data"
CONTAINER_NAME = "graphiti-mon316-falkordb-1"
DATA_PATH = "/var/lib/falkordb/data"


@dataclass(frozen=True)
class BackupResult:
    path: Path
    metadata_path: Path


def backup_path_for_timestamp(root: Path, timestamp: str) -> Path:
    if "/" in timestamp or ".." in timestamp or not re.fullmatch(r"\d{8}-\d{6}", timestamp):
        raise ValueError("invalid backup timestamp")
    path = root / timestamp
    if root.resolve() not in path.resolve().parents:
        raise ValueError("backup path escapes backup root")
    return path


def backup_dry_run(root: Path) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destination = backup_path_for_timestamp(root, timestamp)
    return "\n".join(
        [
            f"Docker volume: {VOLUME_NAME}",
            f"FalkorDB data path: {DATA_PATH}",
            f"Backup destination: {destination}",
            f"Snapshot command: docker exec {CONTAINER_NAME} redis-cli BGSAVE",
            f"Copy command: docker cp {CONTAINER_NAME}:{DATA_PATH}/. {destination}/data",
            "No destructive Compose or volume-removal command is used.",
        ]
    )


def run_backup(*, root: Path, retain_days: int = 30, prune_to_trash: bool = False) -> BackupResult:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destination = backup_path_for_timestamp(root, timestamp)
    data_destination = destination / "data"
    data_destination.mkdir(parents=True, exist_ok=False)
    _run(["docker", "exec", CONTAINER_NAME, "redis-cli", "BGSAVE"])
    _run(["docker", "cp", f"{CONTAINER_NAME}:{DATA_PATH}/.", str(data_destination)])
    metadata = {
        "timestamp": timestamp,
        "volume_name": VOLUME_NAME,
        "container_name": CONTAINER_NAME,
        "data_path": DATA_PATH,
        "created_at": datetime.now(UTC).isoformat(),
    }
    metadata_path = destination / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if prune_to_trash:
        prune_old_backups_to_trash(root, retain_days=retain_days)
    return BackupResult(path=destination, metadata_path=metadata_path)


def prune_old_backups_to_trash(root: Path, *, retain_days: int) -> list[Path]:
    if retain_days < 1:
        raise ValueError("retain_days must be positive")
    backups = sorted(path for path in root.iterdir() if path.is_dir())
    keep = max(retain_days, 1)
    old = backups[:-keep]
    trash_root = Path.home() / ".Trash" / "graphiti-mon316-backups"
    trash_root.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []
    for path in old:
        target = trash_root / path.name
        shutil.move(str(path), str(target))
        moved.append(target)
    return moved


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=600)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or f"command failed: {' '.join(command)}")
