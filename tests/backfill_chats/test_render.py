from __future__ import annotations

from pathlib import Path

from memsearch.backfill.models import Conversation, SourceFile, Turn
from memsearch.backfill.render import output_path_for_conversation, render_conversation


def test_render_conversation_includes_anchor_metadata_and_redacted_turns(tmp_path: Path) -> None:
    source_path = tmp_path / "rollout.jsonl"
    source_path.write_text("{}\n", encoding="utf-8")
    source = SourceFile.from_path(source_path, product="codex", machine="Dominic's MacBook")
    conversation = Conversation(
        source=source,
        product="codex",
        machine="Dominic's MacBook",
        platform_id="codex-1",
        title="Backfill chats",
        started_at="2026-06-01T10:00:00Z",
        ended_at="2026-06-01T10:01:00Z",
        turns=[
            Turn(role="user", text="Use Authorization: Bearer sk-live-secret", timestamp="2026-06-01T10:00:00Z"),
            Turn(role="assistant", text="OPENAI_API_KEY=abc123 is noted", timestamp="2026-06-01T10:01:00Z"),
        ],
    )

    markdown = render_conversation(conversation)

    assert markdown.startswith("## Codex session 2026-06-01T10:00:00Z: Backfill chats")
    assert "<!-- backfill-agent:codex session:platform:codex-1" in markdown
    assert f"transcript:{source_path}" in markdown
    assert "machine:dominics-macbook" in markdown
    assert "- Machine: Dominic's MacBook" in markdown
    assert "- Product: codex" in markdown
    assert "### User" in markdown
    assert "### Assistant" in markdown
    assert "sk-live-secret" not in markdown
    assert "abc123" not in markdown
    assert "[REDACTED]" in markdown


def test_output_path_groups_by_machine_product_and_month(tmp_path: Path) -> None:
    source_path = tmp_path / "session.jsonl"
    source_path.write_text("{}\n", encoding="utf-8")
    source = SourceFile.from_path(source_path, product="claude_code", machine="Dominic's Mac Mini")
    conversation = Conversation(
        source=source,
        product="claude_code",
        machine="Dominic's Mac Mini",
        started_at="2026-06-01T10:00:00Z",
        turns=[Turn(role="user", text="Hello")],
    )

    output = output_path_for_conversation(tmp_path / "imported-chats", conversation)

    assert output == tmp_path / "imported-chats/dominics-mac-mini/claude_code/2026-06.md"


def test_render_uses_export_hash_when_source_is_export(tmp_path: Path) -> None:
    export_path = tmp_path / "conversations.json"
    export_path.write_text("[]", encoding="utf-8")
    source = SourceFile.from_path(export_path, product="chatgpt_export", machine="Dominic's MacBook", source_kind="export")
    conversation = Conversation(
        source=source,
        product="chatgpt_export",
        machine="Dominic's MacBook",
        platform_id="gpt-1",
        started_at="",
        turns=[Turn(role="user", text="Hello")],
    )

    markdown = render_conversation(conversation)

    assert "export_hash:sha256:" in markdown
    assert "transcript:" not in markdown


def test_render_manus_conversation_uses_task_anchor_and_artifacts(tmp_path: Path) -> None:
    source_path = tmp_path / "messages.json"
    source_path.write_text("[]", encoding="utf-8")
    source = SourceFile.from_path(source_path, product="manus_api", machine="Test Mac", source_kind="api")
    conversation = Conversation(
        source=source,
        product="manus_api",
        machine="Test Mac",
        platform_id="task-alpha",
        title="Alpha task",
        started_at="2026-06-04T10:00:00+00:00",
        turns=[Turn(role="user", text="Hello")],
        metadata={
            "task_id": "task-alpha",
            "task_url": "https://manus.im/app/task-alpha",
            "status": "stopped",
            "message_count": 1,
            "artifact_count": 1,
        },
        artifacts=[
            {
                "filename": "notes.md",
                "status": "downloaded",
                "bytes": 12,
                "sha256": "abc123",
                "local_path": str(tmp_path / "attachments" / "notes.md"),
            }
        ],
    )

    markdown = render_conversation(conversation)

    assert "<!-- backfill-agent:manus_api task:task-alpha source:manus_api exported_by_machine:test-mac -->" in markdown
    assert "- Manus task ID: task-alpha" in markdown
    assert "- Manus task URL: https://manus.im/app/task-alpha" in markdown
    assert "## Artefacts" in markdown
    assert "notes.md (downloaded, 12 bytes, sha256:abc123)" in markdown
