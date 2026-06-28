from __future__ import annotations

import json
from pathlib import Path

from memsearch.backfill.parsers.gemini import parse_antigravity_cli_transcript, parse_gemini_chat


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_gemini_chat_keeps_user_and_assistant_turns(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    write_json(
        transcript,
        {
            "sessionId": "416d9ae3-b800-4f8e-bc96-549f521041e9",
            "projectHash": "c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef",
            "startTime": "2026-06-27T07:57:35.868Z",
            "lastUpdated": "2026-06-27T07:57:46.926Z",
            "kind": "main",
            "ignored": {"extra": True},
            "messages": [
                {
                    "id": "u1",
                    "type": "user",
                    "timestamp": "2026-06-27T07:57:35.900Z",
                    "content": "Use memory-recall.",
                },
                {
                    "id": "a1",
                    "type": "assistant",
                    "timestamp": "2026-06-27T07:57:46.000Z",
                    "content": "I found the relevant memory.",
                },
            ],
        },
    )

    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    assert conversation.product == "gemini_cli_chat"
    assert conversation.platform_id == "416d9ae3-b800-4f8e-bc96-549f521041e9"
    assert conversation.title == "Use memory-recall."
    assert conversation.started_at == "2026-06-27T07:57:35.868Z"
    assert conversation.ended_at == "2026-06-27T07:57:46.926Z"
    assert [(turn.role, turn.text, turn.timestamp) for turn in conversation.turns] == [
        ("user", "Use memory-recall.", "2026-06-27T07:57:35.900Z"),
        ("assistant", "I found the relevant memory.", "2026-06-27T07:57:46.000Z"),
    ]
    assert conversation.metadata == {
        "project_hash": "c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef",
        "kind": "main",
        "message_count": 2,
        "last_updated": "2026-06-27T07:57:46.926Z",
        "source_format": "gemini_cli_chat_json_v1",
    }


def test_parse_gemini_chat_prefers_display_content_when_content_is_not_text(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    write_json(
        transcript,
        {
            "sessionId": "session-1",
            "messages": [
                {
                    "type": "user",
                    "timestamp": "2026-06-27T07:57:35.900Z",
                    "content": {"parts": [{"text": "raw object"}]},
                    "displayContent": "Readable prompt",
                },
                {
                    "type": "assistant",
                    "timestamp": "2026-06-27T07:57:46.000Z",
                    "content": [{"text": "Structured answer"}, {"content": "Second line"}],
                },
            ],
        },
    )

    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    assert conversation.title == "Readable prompt"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Readable prompt"),
        ("assistant", "Structured answer\nSecond line"),
    ]


def test_parse_gemini_chat_maps_gemini_role_and_extracts_parts_without_display_content(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    write_json(
        transcript,
        {
            "sessionId": "session-2",
            "messages": [
                {
                    "type": "user",
                    "timestamp": "2026-06-27T07:57:35.900Z",
                    "content": {"parts": [{"text": "Prompt from parts"}]},
                },
                {
                    "type": "gemini",
                    "timestamp": "2026-06-27T07:57:46.000Z",
                    "content": {"parts": [{"text": "Model answer"}, {"text": "Second line"}]},
                },
            ],
        },
    )

    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    assert conversation.title == "Prompt from parts"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Prompt from parts"),
        ("assistant", "Model answer\nSecond line"),
    ]


def test_parse_gemini_chat_requires_top_level_object(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text("[]", encoding="utf-8")

    try:
        parse_gemini_chat(transcript, machine="Test Mac")
    except ValueError as exc:
        assert str(exc) == "Gemini chat JSON must be a top-level object"
    else:
        raise AssertionError("Expected ValueError")


def test_parse_antigravity_cli_transcript_keeps_prompt_answer_and_tool_call(tmp_path: Path) -> None:
    transcript = tmp_path / "brain" / "cli-session" / ".system_generated" / "logs" / "transcript.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "step_index": 0,
                "source": "USER_EXPLICIT",
                "type": "USER_INPUT",
                "created_at": "2026-06-28T16:29:36Z",
                "content": "<USER_REQUEST>\nUse Open Brain read-only.\n</USER_REQUEST>",
            },
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "created_at": "2026-06-28T16:29:40Z",
                "tool_calls": [{"name": "mcp_open-brain_knowledge_graph_health", "args": {"limit": 1}}],
            },
            {
                "step_index": 2,
                "source": "MODEL",
                "type": "GENERIC",
                "created_at": "2026-06-28T16:29:45Z",
                "content": "Open Brain health worked.",
            },
            {
                "step_index": 3,
                "source": "MODEL",
                "type": "RUN_COMMAND",
                "created_at": "2026-06-28T16:29:46Z",
                "content": "Created At: 2026-06-28T16:29:46Z\nraw command output",
            },
        ],
    )

    conversation = parse_antigravity_cli_transcript(transcript, machine="Test Mac")

    assert conversation.product == "antigravity_cli_transcript"
    assert conversation.platform_id == "cli-session"
    assert conversation.title == "Use Open Brain read-only."
    assert conversation.started_at == "2026-06-28T16:29:36Z"
    assert conversation.ended_at == "2026-06-28T16:29:46Z"
    assert [(turn.role, turn.text, turn.timestamp) for turn in conversation.turns] == [
        ("user", "Use Open Brain read-only.", "2026-06-28T16:29:36Z"),
        ("tool", "mcp_open-brain_knowledge_graph_health", "2026-06-28T16:29:40Z"),
        ("assistant", "Open Brain health worked.", "2026-06-28T16:29:45Z"),
    ]
    assert conversation.metadata["source_format"] == "antigravity_cli_transcript_jsonl_v1"
    assert conversation.metadata["tool_call_count"] == 1
