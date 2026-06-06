from __future__ import annotations

import json
from pathlib import Path

from memsearch.backfill.parsers.claude_code import parse_claude_code


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_claude_code_keeps_user_and_assistant_text(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "user",
                "uuid": "u1",
                "sessionId": "session-1",
                "timestamp": "2026-06-01T10:00:00Z",
                "message": {"content": "Remember this decision"},
            },
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "2026-06-01T10:00:01Z",
                "message": {"content": [{"type": "text", "text": "Decision recorded."}]},
            },
        ],
    )

    conversation = parse_claude_code(transcript, machine="Test Mac")

    assert conversation.product == "claude_code"
    assert conversation.platform_id == "session-1"
    assert conversation.title == "Remember this decision"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Remember this decision"),
        ("assistant", "Decision recorded."),
    ]


def test_parse_claude_code_skips_tool_metadata_and_meta_messages(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    write_jsonl(
        transcript,
        [
            {"type": "system", "message": {"content": "system setup"}},
            {"type": "progress", "message": {"content": "progress update"}},
            {"type": "user", "isMeta": True, "message": {"content": "meta reminder"}},
            {"type": "user", "uuid": "u1", "message": {"content": "Check the current version"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "private reasoning"},
                        {"type": "tool_use", "name": "Bash", "input": {"command": "tail memory.md"}},
                        {"type": "text", "text": "Checking."},
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": "stale fact from old journal: memsearch 0.4.4",
                        }
                    ]
                },
            },
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Current version is 0.4.5."}]}},
        ],
    )

    conversation = parse_claude_code(transcript, machine="Test Mac")
    combined = "\n".join(turn.text for turn in conversation.turns)

    assert "Check the current version" in combined
    assert "Checking." in combined
    assert "Current version is 0.4.5." in combined
    assert "stale fact" not in combined
    assert "tail memory.md" not in combined
    assert "private reasoning" not in combined
    assert "meta reminder" not in combined


def test_parse_claude_code_supports_user_text_blocks_and_timestamps(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-06-01T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "First"}, {"type": "tool_result", "content": "skip"}]},
            },
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "2026-06-01T10:00:02Z",
                "message": {"content": [{"type": "text", "text": "Second"}, {"type": "text", "text": "Third"}]},
            },
        ],
    )

    conversation = parse_claude_code(transcript, machine="Test Mac")

    assert conversation.started_at == "2026-06-01T10:00:00Z"
    assert conversation.ended_at == "2026-06-01T10:00:02Z"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "First"),
        ("assistant", "Second\nThird"),
    ]
