from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from .freshness import source_freshness_json
from .gemini_cards import clear_gemini_cards_output, write_gemini_cards
from .inventory import collect_inventory
from .linear_api import LinearApiClient
from .linear_cards import write_linear_cards, write_linear_export
from .manifest import manifest_path, read_manifest, write_manifest
from .manus_api import (
    ManusApiClient,
    ManusPromotionError,
    estimate_manus_export,
    export_manus_run,
    generate_manus_memsearch_cards,
    mark_manus_run_not_indexed,
    promote_manus_run,
    verify_manus_run,
)
from .models import BackfillManifestEntry, Conversation, SourceFile, machine_slug
from .parsers.claude_code import parse_claude_code
from .parsers.claude_desktop import parse_claude_desktop
from .parsers.codex import parse_codex
from .parsers.gemini import parse_gemini_chat
from .parsers.manus import classify_manus_source
from .redact import scan_path_for_secrets, secret_hits_to_json
from .render import output_path_for_conversation, render_conversation
from .scheduler import render_scheduler_plists
from .source_sync import (
    DEFAULT_ANTIGRAVITY_CARD_ROOT,
    DEFAULT_LINEAR_OUTPUT_ROOT,
    DEFAULT_MANUS_CARD_ROOT,
    summary_json,
    sync_antigravity,
    sync_linear,
    sync_manus,
)


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


@main.command("manus-estimate")
def manus_estimate() -> None:
    client = ManusApiClient()
    click.echo(json.dumps(estimate_manus_export(client), indent=2, sort_keys=True))


@main.command("manus-pilot")
@click.option("--limit", type=int, default=10)
@click.option("--machine", required=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path(".local/manus-api-export"))
def manus_pilot(limit: int, machine: str, output: Path) -> None:
    client = ManusApiClient()
    summary = export_manus_run(client, output, machine=machine, limit=limit)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("manus-export")
@click.option("--all", "export_all", is_flag=True)
@click.option("--limit", type=int, default=None)
@click.option("--machine", required=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path(".local/manus-api-export"))
@click.option("--run-id", default=None)
@click.option("--resume", is_flag=True)
def manus_export(export_all: bool, limit: int | None, machine: str, output: Path, run_id: str | None, resume: bool) -> None:
    if not export_all and limit is None:
        raise click.ClickException("Use --all or --limit")
    client = ManusApiClient()
    summary = export_manus_run(client, output, machine=machine, limit=None if export_all else limit, run_id=run_id, resume=resume)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("scan-secrets")
@click.argument("path", type=click.Path(path_type=Path))
def scan_secrets(path: Path) -> None:
    hits = scan_path_for_secrets(path)
    click.echo(secret_hits_to_json(hits))
    if hits:
        raise click.ClickException(f"secret scan found {len(hits)} hit(s)")


@main.command("verify-manus-run")
@click.argument("run_dir", type=click.Path(path_type=Path))
def verify_manus_run_command(run_dir: Path) -> None:
    errors = verify_manus_run(run_dir)
    click.echo(json.dumps({"errors": errors, "ok": not errors}, indent=2, sort_keys=True))
    if errors:
        raise click.ClickException("Manus run verification failed")


@main.command("manus-promote")
@click.option("--run", "run_dir", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--force", is_flag=True)
def manus_promote(run_dir: Path, output: Path, force: bool) -> None:
    try:
        summary = promote_manus_run(run_dir, output, force=force)
    except ManusPromotionError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("manus-cards")
@click.option("--promoted", "promoted_dir", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--force", is_flag=True)
def manus_cards(promoted_dir: Path, output: Path, force: bool) -> None:
    try:
        summary = generate_manus_memsearch_cards(promoted_dir, output, force=force)
    except ManusPromotionError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("manus-mark-not-indexed")
@click.argument("run_dir", type=click.Path(path_type=Path))
@click.option("--reason", required=True)
def manus_mark_not_indexed(run_dir: Path, reason: str) -> None:
    note_path = mark_manus_run_not_indexed(run_dir, reason=reason)
    click.echo(json.dumps({"note_path": str(note_path)}, indent=2, sort_keys=True))


@main.command("linear-export")
@click.option("--machine", required=True)
@click.option("--since", required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--run-id", default=None)
@click.option("--max-issues", type=int, default=None)
def linear_export(machine: str, since: str, output: Path, run_id: str | None, max_issues: int | None) -> None:
    run_id = run_id or "linear-export"
    client = LinearApiClient()
    issues = client.updated_issues(since=since, limit=max_issues)
    summary = write_linear_export(output, issues=issues, machine=machine, since=since, run_id=run_id)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("linear-cards")
@click.option("--machine", required=True)
@click.option("--run", "run_dir", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--force", is_flag=True)
def linear_cards(machine: str, run_dir: Path, output: Path, force: bool) -> None:
    summary = write_linear_cards(run_dir, output, machine=machine, force=force)
    hits = scan_path_for_secrets(output)
    if hits:
        raise click.ClickException(f"Linear card secret scan found {len(hits)} hit(s)")
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command("antigravity-cards")
@click.option("--input", "input_path", type=click.Path(path_type=Path), required=True)
@click.option("--machine", required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--force", is_flag=True)
def antigravity_cards(input_path: Path, machine: str, output: Path, force: bool) -> None:
    paths = _antigravity_input_paths(input_path)
    conversations = [parse_gemini_chat(path, machine=machine) for path in paths]
    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".antigravity-cards-", dir=str(output.parent)) as temp_dir:
        staging = Path(temp_dir) / "cards"
        write_gemini_cards(conversations, staging, machine=machine, force=True)
        hits = scan_path_for_secrets(staging)
        if hits:
            raise click.ClickException(f"Antigravity card secret scan found {len(hits)} hit(s)")
    summary = write_gemini_cards(conversations, output, machine=machine, force=force)
    hits = scan_path_for_secrets(output)
    if hits:
        clear_gemini_cards_output(output)
        raise click.ClickException(f"Antigravity card secret scan found {len(hits)} hit(s)")
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.group("source-sync")
def source_sync_group() -> None:
    """Refresh external sources into MemSearch-ready Markdown cards."""


@source_sync_group.command("linear")
@click.option("--machine", required=True)
@click.option("--since", default=None)
@click.option("--output-root", type=click.Path(path_type=Path), default=DEFAULT_LINEAR_OUTPUT_ROOT)
@click.option("--state-dir", type=click.Path(path_type=Path), default=Path(".local/source-sync-state"))
@click.option("--dry-run", is_flag=True)
@click.option("--index", "index_cards", is_flag=True)
@click.option("--collection", default="memsearch_chunks")
@click.option("--max-issues", type=int, default=None)
def source_sync_linear(
    machine: str,
    since: str | None,
    output_root: Path,
    state_dir: Path,
    dry_run: bool,
    index_cards: bool,
    collection: str,
    max_issues: int | None,
) -> None:
    summary = sync_linear(
        machine=machine,
        since=since,
        output_root=output_root,
        state_dir=state_dir,
        dry_run=dry_run,
        index=index_cards,
        collection=collection,
        max_issues=max_issues,
    )
    click.echo(summary_json(summary))


@source_sync_group.command("manus")
@click.option("--machine", required=True)
@click.option("--since", default=None, help="Alias for --updated-since for Manus date-selective runs.")
@click.option("--created-since", default=None, help="Select Manus tasks created at or after this ISO timestamp/date.")
@click.option("--updated-since", default=None, help="Select Manus tasks updated at or after this ISO timestamp/date.")
@click.option("--output-root", type=click.Path(path_type=Path), default=DEFAULT_MANUS_CARD_ROOT)
@click.option("--state-dir", type=click.Path(path_type=Path), default=Path(".local/source-sync-state"))
@click.option("--all", "export_all", is_flag=True)
@click.option("--run-id", default=None)
@click.option("--resume", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--index", "index_cards", is_flag=True)
@click.option("--collection", default="memsearch_chunks")
@click.option("--max-tasks", type=int, default=None)
def source_sync_manus(
    machine: str,
    since: str | None,
    created_since: str | None,
    updated_since: str | None,
    output_root: Path,
    state_dir: Path,
    export_all: bool,
    run_id: str | None,
    resume: bool,
    dry_run: bool,
    index_cards: bool,
    collection: str,
    max_tasks: int | None,
) -> None:
    summary = sync_manus(
        machine=machine,
        since=since,
        created_since=created_since,
        updated_since=updated_since,
        output_root=output_root,
        state_dir=state_dir,
        export_all=export_all,
        run_id=run_id,
        resume=resume,
        dry_run=dry_run,
        index=index_cards,
        collection=collection,
        max_tasks=max_tasks,
    )
    click.echo(summary_json(summary))


@source_sync_group.command("antigravity")
@click.option("--machine", required=True)
@click.option("--home", type=click.Path(path_type=Path), default=Path.home())
@click.option("--since", default=None)
@click.option("--output-root", type=click.Path(path_type=Path), default=DEFAULT_ANTIGRAVITY_CARD_ROOT)
@click.option(
    "--state-dir",
    type=click.Path(path_type=Path),
    default=Path(".local/source-sync-state"),
    help="Defaults to repo-local .local/source-sync-state; pass explicitly when running outside the memsearch repo.",
)
@click.option("--dry-run", is_flag=True)
@click.option("--index", "index_cards", is_flag=True)
@click.option("--collection", default="memsearch_chunks")
@click.option("--max-sessions", type=int, default=None)
def source_sync_antigravity(
    machine: str,
    home: Path,
    since: str | None,
    output_root: Path,
    state_dir: Path,
    dry_run: bool,
    index_cards: bool,
    collection: str,
    max_sessions: int | None,
) -> None:
    _validate_default_state_dir(state_dir)
    summary = sync_antigravity(
        machine=machine,
        home=home,
        since=since,
        output_root=output_root,
        state_dir=state_dir,
        dry_run=dry_run,
        index=index_cards,
        collection=collection,
        max_sessions=max_sessions,
    )
    click.echo(summary_json(summary))


@main.command("source-freshness")
@click.option("--state-dir", type=click.Path(path_type=Path), default=Path(".local/source-sync-state"))
@click.option("--memory-root", type=click.Path(path_type=Path), default=Path("/Users/dominicmonkhouse/Projects/.memsearch/memory"))
@click.option("--collection", default="memsearch_chunks")
@click.option("--run-proof", is_flag=True)
def source_freshness(state_dir: Path, memory_root: Path, collection: str, run_proof: bool) -> None:
    click.echo(source_freshness_json(state_dir=state_dir, memory_root=memory_root, collection=collection, run_proof=run_proof))


@main.command("scheduler-render")
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--repo-root", type=click.Path(path_type=Path), default=Path.cwd())
@click.option("--machine", default="")
def scheduler_render(output: Path, repo_root: Path, machine: str) -> None:
    if not machine:
        machine = "unknown-machine"
    summary = render_scheduler_plists(output=output, repo_root=repo_root.resolve(), machine=machine)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


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
        sources = _limit_per_product(sources, max(0, limit))

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
    if source.product == "gemini_cli_chat":
        return parse_gemini_chat(source.path, machine=source.machine)
    if source.product in {"claude_desktop_local_agent_jsonl", "claude_desktop_local_agent_json", "claude_desktop_code_session"}:
        return parse_claude_desktop(source)
    if source.product.startswith("manus_"):
        raise ValueError(classify_manus_source(source.path))
    raise ValueError(f"unsupported product: {source.product}")


def _antigravity_input_paths(input_path: Path) -> list[Path]:
    input_path = input_path.expanduser()
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        paths = sorted(path for path in input_path.glob("*.json") if path.is_file())
        if not paths:
            raise click.ClickException(f"no Antigravity JSON files found in {input_path}")
        return paths
    raise click.ClickException(f"missing Antigravity input: {input_path}")


def _validate_default_state_dir(state_dir: Path) -> None:
    if state_dir != Path(".local/source-sync-state"):
        return
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file() and (cwd / "src" / "memsearch").is_dir():
        return
    raise click.ClickException(
        "default --state-dir is repo-local; cd to the memsearch repo or pass --state-dir explicitly"
    )


def _limit_per_product(sources: list[SourceFile], limit: int) -> list[SourceFile]:
    counts: Counter[str] = Counter()
    limited: list[SourceFile] = []
    for source in sources:
        if counts[source.product] >= limit:
            continue
        counts[source.product] += 1
        limited.append(source)
    return limited


if __name__ == "__main__":
    main()
