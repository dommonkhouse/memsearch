from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class IndexResult:
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False


def index_markdown_cards(
    card_dir: Path,
    *,
    collection: str,
    runner: Runner | None = None,
    dry_run: bool = False,
) -> IndexResult:
    command = [
        *_memsearch_module_command(),
        "index",
        str(card_dir),
        "--collection",
        collection,
        "--no-prune",
        "--batch-size",
        "4",
        "--max-chunk-size",
        "3000",
    ]
    if dry_run:
        return IndexResult(command=command, returncode=0, skipped=True)
    run = runner or _run
    completed = run(command)
    return IndexResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def search_proof(
    query: str,
    *,
    collection: str,
    runner: Runner | None = None,
    dry_run: bool = False,
) -> IndexResult:
    command = [*_memsearch_module_command(), "search", query, "--collection", collection, "--json-output"]
    if dry_run:
        return IndexResult(command=command, returncode=0, skipped=True)
    run = runner or _run
    completed = run(command)
    return IndexResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _memsearch_module_command() -> list[str]:
    return [sys.executable, "-m", "memsearch"]
