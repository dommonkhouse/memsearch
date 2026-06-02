from __future__ import annotations

from pathlib import Path

from .models import Conversation, Turn, machine_slug
from .redact import redact_secrets


def render_conversation(conversation: Conversation) -> str:
    heading = _heading(conversation)
    lines = [
        heading,
        _anchor(conversation),
        "",
        f"- Machine: {conversation.machine}",
        f"- Product: {conversation.product}",
        f"- Source: {_source_metadata(conversation)}",
        f"- Conversation key: {conversation.conversation_key}",
    ]
    if conversation.started_at or conversation.ended_at:
        lines.append(f"- Time range: {conversation.started_at or 'unknown'} to {conversation.ended_at or 'unknown'}")
    lines.append("")

    for turn in conversation.turns:
        rendered = _render_turn(turn)
        if rendered:
            lines.extend(rendered)

    return "\n".join(lines).rstrip() + "\n"


def output_path_for_conversation(base_dir: Path, conversation: Conversation) -> Path:
    month = _month_from_timestamp(conversation.started_at)
    return base_dir / machine_slug(conversation.machine) / conversation.product / f"{month}.md"


def _heading(conversation: Conversation) -> str:
    product = conversation.product.replace("_", " ").title()
    suffix = conversation.started_at or conversation.title or conversation.conversation_key
    if conversation.started_at and conversation.title:
        suffix = f"{conversation.started_at}: {conversation.title}"
    return f"## {product} session {suffix}"


def _anchor(conversation: Conversation) -> str:
    fields = [
        f"backfill-agent:{conversation.product}",
        f"session:{conversation.conversation_key}",
        _source_metadata(conversation),
        f"machine:{machine_slug(conversation.machine)}",
    ]
    return "<!-- " + " ".join(fields) + " -->"


def _source_metadata(conversation: Conversation) -> str:
    if conversation.source.source_kind == "export":
        return f"export_hash:{conversation.source.content_hash}"
    return f"transcript:{conversation.source.path}"


def _render_turn(turn: Turn) -> list[str]:
    text = redact_secrets(turn.text).strip()
    if not text:
        return []
    label = turn.role.strip().title() or "Turn"
    timestamp = f" {turn.timestamp}" if turn.timestamp else ""
    return [f"### {label}{timestamp}", "", text, ""]


def _month_from_timestamp(timestamp: str) -> str:
    if len(timestamp) >= 7 and timestamp[4] == "-":
        return timestamp[:7]
    return "unknown"
