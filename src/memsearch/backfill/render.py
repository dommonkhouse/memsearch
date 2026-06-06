from __future__ import annotations

from contextlib import suppress
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
    if conversation.product == "manus_api":
        lines.extend(_render_manus_metadata(conversation))
    lines.append("")

    for turn in conversation.turns:
        rendered = _render_turn(turn)
        if rendered:
            lines.extend(rendered)

    if conversation.artifacts:
        lines.extend(_render_artifacts(conversation))

    return "\n".join(lines).rstrip() + "\n"


def output_path_for_conversation(base_dir: Path, conversation: Conversation) -> Path:
    month = _month_from_timestamp(conversation.started_at)
    return base_dir / machine_slug(conversation.machine) / conversation.product / f"{month}.md"


def _heading(conversation: Conversation) -> str:
    product = conversation.product.replace("_", " ").title()
    title = redact_secrets(conversation.title)
    suffix = conversation.started_at or title or conversation.conversation_key
    if conversation.started_at and conversation.title:
        suffix = f"{conversation.started_at}: {title}"
    return f"## {product} session {suffix}"


def _anchor(conversation: Conversation) -> str:
    if conversation.product == "manus_api":
        task_id = conversation.metadata.get("task_id") or conversation.platform_id
        fields = [
            "backfill-agent:manus_api",
            f"task:{task_id}",
            "source:manus_api",
            f"exported_by_machine:{machine_slug(conversation.machine)}",
        ]
        account_id = conversation.metadata.get("account_id")
        workspace_id = conversation.metadata.get("workspace_id")
        if account_id:
            fields.append(f"account:{account_id}")
        if workspace_id:
            fields.append(f"workspace:{workspace_id}")
        return "<!-- " + " ".join(str(field) for field in fields) + " -->"
    fields = [
        f"backfill-agent:{conversation.product}",
        f"session:{conversation.conversation_key}",
        _source_metadata(conversation),
        f"machine:{machine_slug(conversation.machine)}",
    ]
    return "<!-- " + " ".join(fields) + " -->"


def _source_metadata(conversation: Conversation) -> str:
    if conversation.product == "manus_api":
        return "source:manus_api"
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


def _render_manus_metadata(conversation: Conversation) -> list[str]:
    metadata = conversation.metadata
    lines = [
        f"- Manus task ID: {metadata.get('task_id', conversation.platform_id)}",
        f"- Manus task URL: {metadata.get('task_url', '')}",
        f"- Manus status: {metadata.get('status', '')}",
        f"- Manus message events: {metadata.get('message_count', 0)}",
        f"- Manus artefacts: {metadata.get('artifact_count', len(conversation.artifacts))}",
    ]
    return [line for line in lines if not line.endswith(": ")]


def _render_artifacts(conversation: Conversation) -> list[str]:
    lines = ["## Artefacts", ""]
    for artifact in conversation.artifacts:
        local_path = artifact.get("local_path") or ""
        relative = local_path
        with suppress(ValueError, TypeError):
            relative = str(Path(local_path).relative_to(conversation.source.path.parent.parent))
        lines.append(
            "- "
            + f"{artifact.get('filename', 'attachment')} "
            + f"({artifact.get('status', 'unknown')}, {artifact.get('bytes', 0)} bytes, sha256:{artifact.get('sha256', '')})"
            + (f" -> {relative}" if relative else "")
        )
    lines.append("")
    return lines
