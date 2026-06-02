from __future__ import annotations

import json
from pathlib import Path

import click

from .inventory import collect_inventory


@click.group()
def main() -> None:
    """Backfill chat transcripts into canonical Memsearch markdown."""


@main.command()
@click.option("--home", type=click.Path(path_type=Path), default=Path.home())
@click.option("--machine", required=True)
@click.option("--repo-root", type=click.Path(path_type=Path), default=None)
def inventory(home: Path, machine: str, repo_root: Path | None) -> None:
    files = collect_inventory(home=home, machine=machine, repo_root=repo_root)
    click.echo(
        json.dumps(
            [
                {
                    "product": file.product,
                    "machine": file.machine,
                    "path": str(file.path),
                    "is_fallback": file.is_fallback,
                    "status": file.status,
                }
                for file in files
            ],
            indent=2,
        )
    )
