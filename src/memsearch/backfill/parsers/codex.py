from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Conversation, SourceFile, Turn


def parse_codex(path: str | Path, *, machine: str) -> Conversation:
    rollout_path = Path(path).expanduser()
    source = SourceFile.from_path(rollout_path, product="codex", machine=machine)
    rows = _read_jsonl(rollout_path)
    session_id = _session_id(rows)
    turns = _turns(rows)
    if not turns:
        raise ValueError("unknown_format")
    timestamps = [turn.timestamp for turn in turns if turn.timestamp]

    return Conversation(
        source=source,
        product="codex",
        machine=machine,
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


def _session_id(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("type") != "session_meta":
            continue
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue
        session_id = payload.get("id")
        if session_id:
            return str(session_id)
    return ""


def _turns(rows: list[dict[str, Any]]) -> list[Turn]:
    turns: list[Turn] = []
    for row in rows:
        turn = _event_turn(row) or _response_item_message_turn(row)
        if turn is None:
            continue
        if turns and turns[-1].role == turn.role:
            previous_text = _dedupe_text(turns[-1].text)
            current_text = _dedupe_text(turn.text)
            if previous_text == current_text:
                continue
            if current_text.startswith(previous_text):
                turns[-1] = turn
                continue
        turns.append(turn)
    return turns


def _event_turn(row: dict[str, Any]) -> Turn | None:
    if row.get("type") != "event_msg":
        return None
    payload = row.get("payload", {})
    if not isinstance(payload, dict):
        return None
    msg_type = payload.get("type")
    if msg_type == "user_message":
        text = str(payload.get("message") or "").strip()
        if text:
            return Turn(role="user", text=text, timestamp=str(row.get("timestamp") or ""))
    elif msg_type == "agent_message":
        text = str(payload.get("message") or "").strip()
        if text:
            return Turn(role="assistant", text=text, timestamp=str(row.get("timestamp") or ""))
    return None


def _response_item_message_turn(row: dict[str, Any]) -> Turn | None:
    if row.get("type") != "response_item":
        return None
    payload = row.get("payload", {})
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "message":
        return None
    role = str(payload.get("role") or "").strip().lower()
    if role not in {"user", "assistant"}:
        return None
    text = _content_text(payload.get("content"))
    if not text:
        return None
    return Turn(role=role, text=text, timestamp=str(row.get("timestamp") or ""))


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") not in {"input_text", "output_text", "text"}:
            continue
        text = str(block.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _dedupe_text(text: str) -> str:
    return " ".join(text.split())


def _title_from_turns(turns: list[Turn], limit: int = 80) -> str:
    for turn in turns:
        if turn.role != "user":
            continue
        title = " ".join(turn.text.split())
        return title if len(title) <= limit else title[: limit - 1].rstrip() + "..."
    return ""
