from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import click

from .inventory import collect_inventory
from .manifest import manifest_path, read_manifest, write_manifest
from .models import BackfillManifestEntry, Conversation, SourceFile, machine_slug
from .parsers.claude_code import parse_claude_code
from .parsers.claude_desktop import parse_claude_desktop
from .parsers.codex import parse_codex
from .parsers.manus import classify_manus_source
from .render import output_path_for_conversation, render_conversation


@click.group()
def main() -> None:
    """Backfill chat transcripts into canonical Memsearch markdown."""


@main.command()
@click.option("--home", type=click.Path(path_type=Path), default=Path.home())
@click.option("--machine", required=True)
@click.option("--repo-root", type=click.Path(path_type=Path), default=None)
@click.option("--json-output", is_flag=True)
def inventory(home: Path, machine: str, repo_root: Path | None, json_output: bool) -> None:
    files = collect_inventory(home=home, machine=machine, repo_root=repo_root)
    counts = dict(sorted(Counter(file.product for file in files).items()))
    if json_output:
        click.echo(json.dumps({"machine": machine, "counts": counts, "total": len(files)}, indent=2, sort_keys=True))
        return
    for product, count in counts.items():
        click.echo(f"{product}: {count}")


@main.command()
@click.option("--home", type=click.Path(path_type=Path), default=Path.home())
@click.option("--machine", required=True)
@click.option("--repo-root", type=click.Path(path_type=Path), default=None)
@click.option("--limit", type=int, default=10)
@click.option("--output", type=click.Path(path_type=Path), required=True)
def pilot(home: Path, machine: str, repo_root: Path | None, limit: int, output: Path) -> None:
    summary = _convert(home=home, machine=machine, repo_root=repo_root, output=output, limit=limit)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command()
@click.option("--home", type=click.Path(path_type=Path), default=Path.home())
@click.option("--machine", required=True)
@click.option("--repo-root", type=click.Path(path_type=Path), default=None)
@click.option("--output", type=click.Path(path_type=Path), required=True)
def convert(home: Path, machine: str, repo_root: Path | None, output: Path) -> None:
    summary = _convert(home=home, machine=machine, repo_root=repo_root, output=output, limit=None)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("verify-manifest")
@click.option("--manifest", "manifest_file", type=click.Path(path_type=Path), required=True)
def verify_manifest(manifest_file: Path) -> None:
    entries = read_manifest(manifest_file)
    click.echo(json.dumps({"entries": len(entries)}, indent=2, sort_keys=True))


def _convert(
    *,
    home: Path,
    machine: str,
    repo_root: Path | None,
    output: Path,
    limit: int | None,
) -> dict[str, int | str]:
    output.mkdir(parents=True, exist_ok=True)
    sources = collect_inventory(home=home, machine=machine, repo_root=repo_root)
    if limit is not None:
        sources = sources[: max(0, limit)]

    manifest_file = manifest_path(output, machine_slug(machine))
    existing_entries = read_manifest(manifest_file) if manifest_file.is_file() else []
    entries_by_source = {entry.source_path: entry for entry in existing_entries}
    converted_sections: dict[Path, list[str]] = {}
    converted = skipped = errors = 0

    for source in sources:
        existing = entries_by_source.get(str(source.path))
        if existing and existing.content_hash == source.content_hash and existing.status == "converted":
            skipped += 1
            continue
        try:
            conversation = _parse_source(source)
        except ValueError as exc:
            entries_by_source[str(source.path)] = BackfillManifestEntry.from_source_file(
                source,
                status="skipped",
                last_error=str(exc),
            )
            skipped += 1
            continue
        except Exception as exc:  # pragma: no cover - defensive path recorded in manifest
            entries_by_source[str(source.path)] = BackfillManifestEntry.from_source_file(
                source,
                status="error",
                last_error=str(exc),
            )
            errors += 1
            continue

        output_path = output_path_for_conversation(output, conversation)
        converted_sections.setdefault(output_path, []).append(render_conversation(conversation))
        entries_by_source[str(source.path)] = BackfillManifestEntry.from_source_file(
            source,
            conversation_key=conversation.conversation_key,
            status="converted",
            generated_output_path=str(output_path),
            transcript_fingerprint=conversation.transcript_fingerprint(),
        )
        converted += 1

    for output_path, sections in converted_sections.items():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        existing = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        output_path.write_text(existing + "".join(sections), encoding="utf-8")

    write_manifest(manifest_file, list(entries_by_source.values()))
    return {
        "converted": converted,
        "skipped": skipped,
        "errors": errors,
        "manifest": str(manifest_file),
    }


def _parse_source(source: SourceFile) -> Conversation:
    if source.product == "claude_code":
        return parse_claude_code(source.path, machine=source.machine)
    if source.product == "codex":
        return parse_codex(source.path, machine=source.machine)
    if source.product in {"claude_desktop_local_agent_jsonl", "claude_desktop_local_agent_json", "claude_desktop_code_session"}:
        return parse_claude_desktop(source)
    if source.product.startswith("manus_"):
        raise ValueError(classify_manus_source(source.path))
    raise ValueError(f"unsupported product: {source.product}")


if __name__ == "__main__":
    main()
