from __future__ import annotations

import json
from pathlib import Path

import pytest

from memsearch.backfill.parsers.codex import parse_codex


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_codex_keeps_event_user_and_agent_messages(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {"timestamp": "2026-06-01T09:59:59Z", "type": "session_meta", "payload": {"id": "codex-1"}},
            {"timestamp": "2026-06-01T10:00:00Z", "type": "event_msg", "payload": {"type": "task_started"}},
            {
                "timestamp": "2026-06-01T10:00:01Z",
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "Backfill the chats"},
            },
            {
                "timestamp": "2026-06-01T10:00:02Z",
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "I will build the parser."},
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert conversation.product == "codex"
    assert conversation.platform_id == "codex-1"
    assert conversation.title == "Backfill the chats"
    assert conversation.started_at == "2026-06-01T10:00:01Z"
    assert conversation.ended_at == "2026-06-01T10:00:02Z"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Backfill the chats"),
        ("assistant", "I will build the parser."),
    ]


def test_parse_codex_skips_function_calls_outputs_and_reasoning(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Check the journal"}},
            {
                "type": "response_item",
                "payload": {"type": "function_call", "name": "exec_command", "arguments": json.dumps({"cmd": "tail memory.md"})},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "output": "Process exited with code 0\nOutput:\nstale fact: memsearch version 0.4.4",
                },
            },
            {"type": "response_item", "payload": {"type": "reasoning", "summary": [{"text": "private reasoning"}]}},
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Current version is 0.4.5."}},
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")
    combined = "\n".join(turn.text for turn in conversation.turns)

    assert "Check the journal" in combined
    assert "Current version is 0.4.5." in combined
    assert "tail memory.md" not in combined
    assert "stale fact" not in combined
    assert "private reasoning" not in combined


def test_parse_codex_uses_response_item_messages_as_fallback(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {
                "timestamp": "2026-06-01T10:00:01Z",
                "type": "response_item",
                "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Fallback user"}]},
            },
            {
                "timestamp": "2026-06-01T10:00:02Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Fallback assistant"}, {"type": "text", "text": "Second line"}],
                },
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Fallback user"),
        ("assistant", "Fallback assistant\nSecond line"),
    ]


def test_parse_codex_does_not_duplicate_response_item_messages_when_events_exist(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Event user"}},
            {
                "type": "response_item",
                "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Event user"}]},
            },
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Event assistant"}},
            {
                "type": "response_item",
                "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Event assistant"}]},
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Event user"),
        ("assistant", "Event assistant"),
    ]


def test_parse_codex_dedupes_near_equal_response_item_mirrors(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    event_text = "Done. I read the guide.\n\nPlan is complete."
    response_text = "Done. I read the guide.\nPlan is complete."
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "agent_message", "message": event_text}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_text}],
                },
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [("assistant", event_text)]


def test_parse_codex_replaces_short_event_mirror_with_full_response_item(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    event_text = "Done. Report written."
    response_text = "Done. Report written.\n\n<oai-mem-citation>citation block</oai-mem-citation>"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "agent_message", "message": event_text}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": response_text}],
                },
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [("assistant", response_text)]


def test_parse_codex_skips_short_response_mirror_after_full_event_item(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    event_text = "<image>clipboard block</image>\n\n## My request for Codex:\nRun the reingest"
    response_text = "<image>clipboard block</image>\n\n## My request for Codex:"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "user_message", "message": event_text}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": response_text}],
                },
            },
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [("user", event_text)]


def test_parse_codex_keeps_mixed_event_and_response_item_only_turns(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Event-only user"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Response-only assistant"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Response-only follow-up"}],
                },
            },
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Event-only answer"}},
        ],
    )

    conversation = parse_codex(rollout, machine="Test Mac")

    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Event-only user"),
        ("assistant", "Response-only assistant"),
        ("user", "Response-only follow-up"),
        ("assistant", "Event-only answer"),
    ]


def test_parse_codex_rejects_empty_rollout_without_turns(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "response_item", "payload": {"type": "reasoning", "summary": [{"text": "private reasoning"}]}},
        ],
    )

    with pytest.raises(ValueError, match="unknown_format"):
        parse_codex(rollout, machine="Test Mac")
