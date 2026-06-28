from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Conversation, SourceFile, Turn, _extract_text


def parse_antigravity_source(path: str | Path, *, machine: str) -> Conversation:
    transcript_path = Path(path).expanduser()
    if transcript_path.name == "transcript.jsonl" and ".system_generated" in transcript_path.parts:
        return parse_antigravity_cli_transcript(transcript_path, machine=machine)
    return parse_gemini_chat(transcript_path, machine=machine)


def parse_gemini_chat(path: str | Path, *, machine: str) -> Conversation:
    transcript_path = Path(path).expanduser()
    source = SourceFile.from_path(transcript_path, product="gemini_cli_chat", machine=machine)
    payload = _read_json(transcript_path)
    messages = payload.get("messages")
    message_rows = messages if isinstance(messages, list) else []
    turns: list[Turn] = []

    for message in message_rows:
        if not isinstance(message, dict):
            continue
        role = _message_role(message)
        text = _message_text(message)
        if role and text:
            turns.append(Turn(role=role, text=text, timestamp=str(message.get("timestamp") or "")))

    start_time = str(payload.get("startTime") or "")
    last_updated = str(payload.get("lastUpdated") or "")

    return Conversation(
        source=source,
        product="gemini_cli_chat",
        machine=machine,
        platform_id=str(payload.get("sessionId") or ""),
        title=_title_from_turns(turns),
        started_at=start_time,
        ended_at=last_updated,
        turns=turns,
        metadata={
            "project_hash": str(payload.get("projectHash") or ""),
            "kind": str(payload.get("kind") or ""),
            "message_count": len(message_rows),
            "last_updated": last_updated,
            "source_format": "gemini_cli_chat_json_v1",
        },
    )


def parse_antigravity_cli_transcript(path: str | Path, *, machine: str) -> Conversation:
    transcript_path = Path(path).expanduser()
    source = SourceFile.from_path(transcript_path, product="antigravity_cli_transcript", machine=machine)
    session_id = _antigravity_cli_session_id(transcript_path)
    rows = list(_iter_jsonl(transcript_path))
    turns: list[Turn] = []
    tool_call_count = 0
    created_at_values: list[str] = []

    for row in rows:
        timestamp = str(row.get("created_at") or row.get("timestamp") or "")
        if timestamp:
            created_at_values.append(timestamp)
        step_type = str(row.get("type") or "")
        source_name = str(row.get("source") or "")

        if step_type == "USER_INPUT":
            text = _extract_user_request(str(row.get("content") or ""))
            if text:
                turns.append(Turn(role="user", text=text, timestamp=timestamp))
            continue

        tool_calls = row.get("tool_calls")
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if isinstance(call, dict):
                    tool_call_count += 1
                    name = str(call.get("name") or "unknown")
                    turns.append(Turn(role="tool", text=name, timestamp=timestamp))
            continue

        content = str(row.get("content") or "")
        if source_name == "MODEL" and content and not content.startswith("Created At:"):
            turns.append(Turn(role="assistant", text=content, timestamp=timestamp))

    started_at = min(created_at_values) if created_at_values else ""
    ended_at = max(created_at_values) if created_at_values else ""
    return Conversation(
        source=source,
        product="antigravity_cli_transcript",
        machine=machine,
        platform_id=session_id,
        title=_title_from_turns(turns),
        started_at=started_at,
        ended_at=ended_at,
        turns=turns,
        metadata={
            "project_hash": "antigravity-cli",
            "kind": "main",
            "message_count": len(rows),
            "last_updated": ended_at,
            "source_format": "antigravity_cli_transcript_jsonl_v1",
            "tool_call_count": tool_call_count,
        },
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Gemini chat JSON must be a top-level object")
    return payload


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    display_content = message.get("displayContent")
    if isinstance(display_content, str) and display_content.strip():
        return display_content.strip()

    return _extract_text(content).strip()


def _message_role(message: dict[str, Any]) -> str:
    role = str(message.get("type") or "").strip().lower()
    if role in {"gemini", "model"}:
        return "assistant"
    return role


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _extract_user_request(content: str) -> str:
    import re

    match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, flags=re.S)
    return match.group(1).strip() if match else content.strip()


def _antigravity_cli_session_id(path: Path) -> str:
    if "brain" in path.parts:
        index = path.parts.index("brain")
        if index + 1 < len(path.parts):
            return path.parts[index + 1]
    return path.stem


def _title_from_turns(turns: list[Turn], limit: int = 120) -> str:
    for turn in turns:
        if turn.role != "user":
            continue
        title = " ".join(turn.text.split())
        if title:
            return title[:limit].rstrip()
    return ""
