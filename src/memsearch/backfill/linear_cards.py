from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .linear_api import LinearIssue
from .models import machine_slug
from .redact import REDACTOR_VERSION, redact_secrets


def render_linear_issue_card(issue: LinearIssue, *, machine: str) -> str:
    labels = ", ".join(issue.labels)
    lines = [
        f"## Linear issue {issue.identifier}: {redact_secrets(issue.title)}",
        f"<!-- backfill-agent:linear issue:{issue.identifier} source:linear machine:{machine_slug(machine)} -->",
        "",
        f"- Linear issue ID: {issue.identifier}",
        f"- Linear URL: {redact_secrets(issue.url)}",
        f"- Machine: {machine}",
        f"- State: {issue.state or 'unknown'}",
        f"- Team: {issue.team or 'unknown'}",
        f"- Updated: {issue.updated_at or 'unknown'}",
    ]
    if issue.assignee:
        lines.append(f"- Assignee: {redact_secrets(issue.assignee)}")
    if labels:
        lines.append(f"- Labels: {redact_secrets(labels)}")
    lines.append("")
    if issue.description.strip():
        lines.extend(["Description:", _bullet(redact_secrets(issue.description), 1800), ""])
    visible_comments = [comment for comment in issue.comments if str(comment.get("body") or "").strip()]
    if visible_comments:
        lines.append("Recent comments:")
        for comment in visible_comments[-5:]:
            user = redact_secrets(str(comment.get("user") or "unknown"))
            timestamp = comment.get("updated_at") or comment.get("created_at") or ""
            lines.append(_bullet(f"{user} {timestamp}: {redact_secrets(str(comment.get('body') or ''))}", 1000))
        lines.append("")
    lines.append("---")
    return "\n".join(lines)


def write_linear_export(
    run_dir: Path, *, issues: list[LinearIssue], machine: str, since: str, run_id: str
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "machine": machine,
        "since": since,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issue_count": len(issues),
        "issues": [issue.to_json() for issue in issues],
    }
    _write_json(run_dir / "issues.json", payload)
    summary = {
        "run_id": run_id,
        "machine": machine,
        "since": since,
        "output_dir": str(run_dir),
        "issue_count": len(issues),
        "issues_path": str(run_dir / "issues.json"),
    }
    _write_json(run_dir / "summary.json", summary)
    return summary


def load_linear_export(run_dir: Path) -> tuple[list[LinearIssue], dict[str, Any]]:
    payload = json.loads((run_dir / "issues.json").read_text(encoding="utf-8"))
    return [LinearIssue.from_json(row) for row in payload.get("issues", [])], payload


def write_linear_cards(
    run_dir: Path, output_dir: Path, *, machine: str | None = None, force: bool = False
) -> dict[str, Any]:
    output_dir = output_dir.expanduser()
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output_dir}")
    if force and output_dir.exists():
        _empty_directory(output_dir)
    issues, payload = load_linear_export(run_dir)
    machine = machine or str(payload.get("machine") or "")
    output_root = output_dir / "memory" / "linear" / machine_slug(machine or "unknown")
    output_root.mkdir(parents=True, exist_ok=True)

    cards_by_month: dict[str, list[str]] = defaultdict(list)
    for issue in sorted(issues, key=lambda item: (item.updated_at, item.identifier)):
        month = _month(issue.updated_at or issue.created_at)
        cards_by_month[month].append(render_linear_issue_card(issue, machine=machine))

    files: list[dict[str, Any]] = []
    for month, cards in sorted(cards_by_month.items()):
        text = "\n".join(cards).rstrip() + ("\n" if cards else "")
        path = output_root / f"{month}.md"
        path.write_text(text, encoding="utf-8")
        files.append(
            {
                "path": str(path),
                "byte_size": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    summary = {
        "run_id": str(payload.get("run_id") or run_dir.name),
        "source_run_path": str(run_dir),
        "output_dir": str(output_dir),
        "machine": machine,
        "markdown_files": len(files),
        "issue_cards": len(issues),
        "card_format": "linear_issue_card_v1",
    }
    _write_json(
        output_dir / "card-manifest.json",
        {
            **summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "redactor_version": REDACTOR_VERSION,
            "issue_ids": sorted(issue.identifier for issue in issues if issue.identifier),
            "files": files,
        },
    )
    _write_json(output_dir / "summary.json", summary)
    return summary


def _month(timestamp: str) -> str:
    return timestamp[:7] if len(timestamp) >= 7 else "unknown-month"


def _bullet(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) > limit:
        clean = clean[: limit - 3].rstrip() + "..."
    return "- " + clean


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _empty_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _empty_directory(child)
            child.rmdir()
        else:
            child.unlink()
