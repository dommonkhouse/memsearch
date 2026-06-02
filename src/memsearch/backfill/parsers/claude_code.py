from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Conversation, SourceFile, Turn


def parse_claude_code(path: str | Path, *, machine: str) -> Conversation:
    transcript_path = Path(path).expanduser()
    source = SourceFile.from_path(transcript_path, product="claude_code", machine=machine)
    rows = _read_jsonl(transcript_path)
    turns: list[Turn] = []
    session_id = ""
    timestamps: list[str] = []

    for row in rows:
        if not session_id:
            session_id = str(row.get("sessionId") or row.get("session_id") or "")
        timestamp = str(row.get("timestamp") or "")
        msg_type = row.get("type", "")
        if msg_type not in {"user", "assistant"}:
            continue
        if row.get("isMeta"):
            continue

        message = row.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None

        if msg_type == "user":
            text = _user_text(content)
            if not text:
                continue
            turns.append(Turn(role="user", text=text, timestamp=timestamp))
            if timestamp:
                timestamps.append(timestamp)
            continue

        text = _assistant_text(content)
        if not text:
            continue
        turns.append(Turn(role="assistant", text=text, timestamp=timestamp))
        if timestamp:
            timestamps.append(timestamp)

    title = _title_from_turns(turns)
    return Conversation(
        source=source,
        product="claude_code",
        machine=machine,
        platform_id=session_id,
        title=title,
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
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
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
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
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
