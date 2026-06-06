from __future__ import annotations

import json
from pathlib import Path

import pytest

from memsearch.backfill.models import SourceFile
from memsearch.backfill.parsers.claude_desktop import parse_claude_desktop
from memsearch.backfill.render import render_conversation


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_claude_desktop_local_agent_jsonl_keeps_user_assistant_text(tmp_path: Path) -> None:
    transcript = (
        tmp_path
        / "Library/Application Support/Claude/local-agent-mode-sessions/account/project/local_1/.claude/projects/foo/session.jsonl"
    )
    write_jsonl(
        transcript,
        [
            {"type": "queue-operation", "sessionId": "local-1", "timestamp": "2026-06-01T09:59:59Z"},
            {
                "type": "user",
                "sessionId": "local-1",
                "timestamp": "2026-06-01T10:00:00Z",
                "message": {"role": "user", "content": "Cowork-only request"},
            },
            {
                "type": "assistant",
                "sessionId": "local-1",
                "timestamp": "2026-06-01T10:00:01Z",
                "message": {"content": [{"type": "text", "text": "Cowork-only answer"}]},
            },
        ],
    )

    conversation = parse_claude_desktop(SourceFile.from_path(transcript, product="claude_desktop_local_agent_jsonl", machine="Test Mac"))

    assert conversation.product == "claude_desktop_cowork"
    assert conversation.platform_id == "local-1"
    assert [(turn.role, turn.text) for turn in conversation.turns] == [
        ("user", "Cowork-only request"),
        ("assistant", "Cowork-only answer"),
    ]


def test_parse_claude_desktop_excludes_audit_logs_subagents_and_code_sessions(tmp_path: Path) -> None:
    audit = tmp_path / "Library/Application Support/Claude/local-agent-mode-sessions/account/project/local_1/audit.jsonl"
    subagent = (
        tmp_path
        / "Library/Application Support/Claude/local-agent-mode-sessions/account/project/local_1/.claude/projects/foo/subagents/agent.jsonl"
    )
    code_session = tmp_path / "Library/Application Support/Claude/claude-code-sessions/account/project/local_1.json"
    metadata = tmp_path / "Library/Application Support/Claude/local-agent-mode-sessions/account/project/local_1.json"
    for path in [audit, subagent]:
        write_jsonl(path, [{"type": "user", "_audit_timestamp": "2026", "message": {"content": "Do not ingest"}}])
    code_session.parent.mkdir(parents=True, exist_ok=True)
    code_session.write_text(json.dumps({"sessionId": "local_1", "completedTurns": 2}), encoding="utf-8")
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps({"sessionId": "local_1", "initialMessage": "metadata only"}), encoding="utf-8")

    cases = [
        (audit, "claude_desktop_local_agent_jsonl", "audit_log"),
        (subagent, "claude_desktop_local_agent_jsonl", "subagent_transcript"),
        (code_session, "claude_desktop_code_session", "possible_duplicate_claude_code"),
        (metadata, "claude_desktop_local_agent_json", "unknown_format"),
    ]

    for path, product, reason in cases:
        with pytest.raises(ValueError, match=reason):
            parse_claude_desktop(SourceFile.from_path(path, product=product, machine="Test Mac"))


def test_parse_claude_desktop_render_redacts_secret_like_turn_values(tmp_path: Path) -> None:
    transcript = (
        tmp_path
        / "Library/Application Support/Claude/local-agent-mode-sessions/account/project/local_1/.claude/projects/foo/session.jsonl"
    )
    write_jsonl(
        transcript,
        [
            {"type": "user", "sessionId": "local-1", "message": {"content": "Use OPENAI_API_KEY=abc123"}},
            {"type": "assistant", "sessionId": "local-1", "message": {"content": [{"type": "text", "text": "Bearer sk-secret"}]}},
        ],
    )

    conversation = parse_claude_desktop(SourceFile.from_path(transcript, product="claude_desktop_local_agent_jsonl", machine="Test Mac"))
    markdown = render_conversation(conversation)

    assert "abc123" not in markdown
    assert "sk-secret" not in markdown
    assert "[REDACTED]" in markdown
