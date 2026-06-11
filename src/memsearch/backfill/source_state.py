from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceSyncState:
    source: str
    machine: str = ""
    last_success_at: str = ""
    last_failure_at: str = ""
    last_since: str = ""
    last_run_id: str = ""
    item_count: int = 0
    card_count: int = 0
    last_error: str = ""
    task_snapshots: dict[str, str] = field(default_factory=dict)
    proof_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any], *, source: str) -> SourceSyncState:
        return cls(
            source=str(data.get("source") or source),
            machine=str(data.get("machine") or ""),
            last_success_at=str(data.get("last_success_at") or ""),
            last_failure_at=str(data.get("last_failure_at") or ""),
            last_since=str(data.get("last_since") or ""),
            last_run_id=str(data.get("last_run_id") or ""),
            item_count=int(data.get("item_count") or 0),
            card_count=int(data.get("card_count") or 0),
            last_error=str(data.get("last_error") or ""),
            task_snapshots={str(k): str(v) for k, v in dict(data.get("task_snapshots") or {}).items()},
            proof_ids=[str(item) for item in data.get("proof_ids") or []],
        )

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    def record_success(
        self,
        *,
        machine: str,
        run_id: str,
        since: str,
        item_count: int,
        card_count: int,
        proof_ids: list[str] | None = None,
        task_snapshots: dict[str, str] | None = None,
    ) -> SourceSyncState:
        return SourceSyncState(
            source=self.source,
            machine=machine,
            last_success_at=utc_now_iso(),
            last_failure_at=self.last_failure_at,
            last_since=since,
            last_run_id=run_id,
            item_count=item_count,
            card_count=card_count,
            last_error="",
            task_snapshots=task_snapshots if task_snapshots is not None else self.task_snapshots,
            proof_ids=proof_ids if proof_ids is not None else self.proof_ids,
        )

    def record_failure(self, *, machine: str, error: str) -> SourceSyncState:
        return SourceSyncState(
            source=self.source,
            machine=machine,
            last_success_at=self.last_success_at,
            last_failure_at=utc_now_iso(),
            last_since=self.last_since,
            last_run_id=self.last_run_id,
            item_count=self.item_count,
            card_count=self.card_count,
            last_error=error,
            task_snapshots=self.task_snapshots,
            proof_ids=self.proof_ids,
        )


def state_path(state_dir: Path, source: str) -> Path:
    return state_dir.expanduser() / f"{source}.json"


def read_source_state(state_dir: Path, source: str) -> SourceSyncState:
    path = state_path(state_dir, source)
    if not path.is_file():
        return SourceSyncState(source=source)
    return SourceSyncState.from_json(json.loads(path.read_text(encoding="utf-8")), source=source)


def write_source_state(state_dir: Path, state: SourceSyncState) -> Path:
    state_dir = state_dir.expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_path(state_dir, state.source)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


@contextmanager
def source_lock(state_dir: Path, source: str) -> Iterator[Path]:
    state_dir = state_dir.expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{source}.lock"
    try:
        if path.exists() and _stale_lock(path):
            path.unlink()
        with path.open("x", encoding="utf-8") as handle:
            handle.write(utc_now_iso() + "\n")
            handle.write(f"pid={os.getpid()}\n")
        yield path
    finally:
        if path.exists():
            path.unlink()


def _stale_lock(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    pid_line = next((line for line in lines if line.startswith("pid=")), "")
    if not pid_line:
        return False
    try:
        pid = int(pid_line.removeprefix("pid="))
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False
