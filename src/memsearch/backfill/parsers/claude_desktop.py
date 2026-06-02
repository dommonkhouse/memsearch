from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Conversation, SourceFile, Turn


def parse_claude_desktop(source: SourceFile, *, include_subagents: bool = False) -> Conversation:
    path = source.path
    _validate_source_path(source, include_subagents=include_subagents)
    if path.suffix == ".jsonl":
        return _parse_local_agent_jsonl(source)
    raise ValueError("unknown_format")


def _validate_source_path(source: SourceFile, *, include_subagents: bool) -> None:
    path = source.path
    path_text = str(path)
    if source.product == "claude_desktop_code_session" or "claude-code-sessions" in path_text:
        raise ValueError("possible_duplicate_claude_code")
    if "local-agent-mode-sessions" not in path_text:
        raise ValueError("unknown_format")
    if path.name == "audit.jsonl":
        raise ValueError("audit_log")
    if "subagents" in path.parts and not include_subagents:
        raise ValueError("subagent_transcript")
    if any(part in path.parts for part in {".claude-plugin", "node_modules", ".venv", "site-packages", "todos"}):
        raise ValueError("plugin_or_dependency")
    if path.name in {".credentials.json", "manifest.json", "plugin.json"}:
        raise ValueError("plugin_or_dependency")


def _parse_local_agent_jsonl(source: SourceFile) -> Conversation:
    rows = _read_jsonl(source.path)
    if any("_audit_timestamp" in row for row in rows):
        raise ValueError("audit_log")

    turns: list[Turn] = []
    session_id = ""
    timestamps: list[str] = []
    for row in rows:
        if not session_id:
            session_id = str(row.get("sessionId") or row.get("session_id") or "")
        msg_type = row.get("type")
        if msg_type not in {"user", "assistant"} or row.get("isMeta"):
            continue
        timestamp = str(row.get("timestamp") or "")
        message = row.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        text = _user_text(content) if msg_type == "user" else _assistant_text(content)
        if not text:
            continue
        turns.append(Turn(role="user" if msg_type == "user" else "assistant", text=text, timestamp=timestamp))
        if timestamp:
            timestamps.append(timestamp)

    if not turns:
        raise ValueError("unknown_format")

    return Conversation(
        source=source,
        product="claude_desktop_cowork",
        machine=source.machine,
        platform_id=session_id,
        title=_title_from_turns(turns),
        started_at=timestamps[0] if timestamps else "",
        ended_at=timestamps[-1] if timestamps else "",
        turns=turns,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _user_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = str(block.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _assistant_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = str(block.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _title_from_turns(turns: list[Turn], limit: int = 80) -> str:
    for turn in turns:
        if turn.role != "user":
            continue
        title = " ".join(turn.text.split())
        return title if len(title) <= limit else title[: limit - 1].rstrip() + "..."
    return ""
