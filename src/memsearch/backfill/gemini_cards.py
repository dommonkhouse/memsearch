from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Conversation, machine_slug
from .redact import REDACTOR_VERSION, redact_secrets

CARD_FORMAT = "antigravity_gemini_session_card_v1"
GENERATED_OUTPUT_ENTRIES = {"memory", "card-manifest.json", "summary.json"}
GENERATED_TOP_LEVEL_FILES = {"card-manifest.json", "summary.json"}
GENERATED_MONTH_FILE_RE = re.compile(r"^\d{4}-\d{2}\.md$")
HOOK_CONTEXT_RE = re.compile(r"\s*<hook_context>.*", re.DOTALL)


def render_gemini_session_card(conversation: Conversation) -> str:
    session_id = conversation.platform_id or "unknown-session"
    project_hash = str(conversation.metadata.get("project_hash") or "")
    message_count = int(conversation.metadata.get("message_count") or len(conversation.turns))
    start = conversation.started_at or "unknown-start"
    end = conversation.ended_at or str(conversation.metadata.get("last_updated") or "unknown-end")
    title = redact_secrets(_card_text(conversation.title or _first_turn_text(conversation, "user") or session_id))
    user_request = _excerpt(_card_text(_first_turn_text(conversation, "user")), 1200)
    assistant_outcome = _excerpt(_card_text(_last_turn_text(conversation, "assistant")), 1200)
    role_counts = Counter(turn.role for turn in conversation.turns)
    role_summary = ", ".join(f"{role}:{count}" for role, count in sorted(role_counts.items())) or "none"
    notable_types = ", ".join(sorted(role_counts)) or "none"

    lines = [
        f"## Antigravity session {start}: {title}",
        "<!-- "
        f"backfill-agent:antigravity source:{conversation.product} session:{session_id} "
        f"project_hash:{project_hash} machine:{machine_slug(conversation.machine)}"
        " -->",
        "",
        f"- Machine: {redact_secrets(conversation.machine)}",
        f"- Project hash: {redact_secrets(project_hash or 'unknown')}",
        f"- Source path: {redact_secrets(str(conversation.source.path))}",
        f"- Session ID: {redact_secrets(session_id)}",
        f"- Message count: {message_count}",
        f"- Time range: {start} to {end}",
        "Classification: current",
        f"Evidence: source transcript {redact_secrets(str(conversation.source.path))}; session {redact_secrets(session_id)}",
        "",
        "### User request",
        "",
        redact_secrets(user_request or "No user request captured."),
        "",
        "### Assistant outcome",
        "",
        redact_secrets(assistant_outcome or "No assistant outcome captured."),
        "",
        "### Conversation signals",
        "",
        f"- Role counts: {role_summary}",
        f"- Notable message types: {notable_types}",
        "",
        "---",
    ]
    return "\n".join(lines)


def write_gemini_cards(
    conversations: list[Conversation],
    output_dir: Path,
    *,
    machine: str,
    force: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser()
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output_dir}")
    if force and output_dir.exists():
        _empty_generated_output(output_dir)
    output_root = output_dir / "memory" / "antigravity" / "gemini_cli"
    output_root.mkdir(parents=True, exist_ok=True)

    cards_by_month: dict[str, list[str]] = defaultdict(list)
    ordered = sorted(conversations, key=lambda item: (item.started_at, item.platform_id, str(item.source.path)))
    for conversation in ordered:
        cards_by_month[_month(conversation.started_at)].append(render_gemini_session_card(conversation))

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

    session_ids = sorted(conversation.platform_id for conversation in conversations if conversation.platform_id)
    source_paths = sorted(str(conversation.source.path) for conversation in conversations)
    summary = {
        "output_dir": str(output_dir),
        "machine": machine,
        "markdown_files": len(files),
        "card_count": len(conversations),
        "card_format": CARD_FORMAT,
    }
    _write_json(
        output_dir / "card-manifest.json",
        {
            **summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "redactor_version": REDACTOR_VERSION,
            "session_ids": session_ids,
            "source_paths": source_paths,
            "files": files,
        },
    )
    _write_json(output_dir / "summary.json", summary)
    return summary


def clear_gemini_cards_output(output_dir: Path) -> None:
    output_dir = output_dir.expanduser()
    if output_dir.exists():
        _empty_generated_output(output_dir)


def _first_turn_text(conversation: Conversation, role: str) -> str:
    for turn in conversation.turns:
        if turn.role == role and turn.text.strip():
            return turn.text
    return ""


def _last_turn_text(conversation: Conversation, role: str) -> str:
    for turn in reversed(conversation.turns):
        if turn.role == role and turn.text.strip():
            return turn.text
    return ""


def _excerpt(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) > limit:
        return clean[: limit - 3].rstrip() + "..."
    return clean


def _card_text(value: str) -> str:
    return HOOK_CONTEXT_RE.sub("", value).strip()


def _month(timestamp: str) -> str:
    return timestamp[:7] if len(timestamp) >= 7 else "unknown-month"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _empty_generated_output(path: Path) -> None:
    unexpected = _unexpected_generated_output_entries(path)
    if unexpected:
        raise FileExistsError(f"refusing to overwrite non-generated output entries: {', '.join(unexpected)}")
    for filename in GENERATED_TOP_LEVEL_FILES:
        child = path / filename
        if child.is_file():
            child.unlink()
    gemini_root = path / "memory" / "antigravity" / "gemini_cli"
    if gemini_root.is_dir():
        for child in gemini_root.iterdir():
            child.unlink()
        _remove_empty_parents(gemini_root, stop=path)


def _unexpected_generated_output_entries(path: Path) -> list[str]:
    unexpected: list[str] = []
    for child in path.iterdir():
        if child.name in GENERATED_TOP_LEVEL_FILES:
            if not child.is_file():
                unexpected.append(child.name)
            continue
        if child.name == "memory":
            unexpected.extend(_unexpected_memory_entries(child, root=path))
            continue
        unexpected.append(child.name)
    return sorted(unexpected)


def _unexpected_memory_entries(memory_dir: Path, *, root: Path) -> list[str]:
    unexpected: list[str] = []
    if not memory_dir.is_dir():
        return [str(memory_dir.relative_to(root))]
    antigravity_dir = memory_dir / "antigravity"
    unexpected.extend(str(child.relative_to(root)) for child in memory_dir.iterdir() if child != antigravity_dir)
    if not antigravity_dir.exists():
        return unexpected
    if not antigravity_dir.is_dir():
        return [*unexpected, str(antigravity_dir.relative_to(root))]
    gemini_dir = antigravity_dir / "gemini_cli"
    unexpected.extend(str(child.relative_to(root)) for child in antigravity_dir.iterdir() if child != gemini_dir)
    if not gemini_dir.exists():
        return unexpected
    if not gemini_dir.is_dir():
        return [*unexpected, str(gemini_dir.relative_to(root))]
    unexpected.extend(
        str(child.relative_to(root))
        for child in gemini_dir.iterdir()
        if not child.is_file() or not GENERATED_MONTH_FILE_RE.match(child.name)
    )
    return unexpected


def _remove_empty_parents(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
