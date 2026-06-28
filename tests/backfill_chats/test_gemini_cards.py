from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from memsearch.backfill import cli as backfill_cli
from memsearch.backfill.gemini_cards import render_gemini_session_card, write_gemini_cards
from memsearch.backfill.parsers.gemini import parse_gemini_chat
from memsearch.backfill.redact import scan_path_for_secrets
from memsearch.graphiti.candidates import build_candidate_report


def write_session(path: Path, *, session_id: str = "session-1", started_at: str = "2026-06-27T07:57:35.868Z") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "sessionId": session_id,
                "projectHash": "c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef",
                "startTime": started_at,
                "lastUpdated": "2026-06-27T07:58:46.926Z",
                "kind": "main",
                "messages": [
                    {
                        "id": "u1",
                        "type": "user",
                        "timestamp": started_at,
                        "content": "Use OPENAI_API_KEY=abc123456789 to test this.",
                    },
                    {
                        "id": "a1",
                        "type": "gemini",
                        "timestamp": "2026-06-27T07:58:46.000Z",
                        "content": "I found the relevant memory.",
                    },
                    {
                        "id": "tool1",
                        "type": "tool",
                        "timestamp": "2026-06-27T07:58:47.000Z",
                        "content": {"parts": [{"text": "large raw payload that should not be dumped"}]},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def run_backfill(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("MEMSEARCH_DIR", None)
    return subprocess.run(
        [sys.executable, "-m", "memsearch.backfill.cli", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_gemini_card_contains_anchor_sections_and_redacts_secrets(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    write_session(transcript)
    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    card = render_gemini_session_card(conversation)

    assert "## Antigravity session 2026-06-27T07:57:35.868Z: Use OPENAI_API_KEY=[REDACTED] to test this." in card
    assert "backfill-agent:antigravity source:gemini_cli_chat session:session-1" in card
    assert "project_hash:c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef" in card
    assert "machine:test-mac" in card
    assert "- Session ID: session-1" in card
    assert "- Project hash: c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef" in card
    assert f"- Source path: {transcript}" in card
    assert "- Message count: 3" in card
    assert "Classification: current" in card
    assert f"Evidence: source transcript {transcript}; session session-1" in card
    assert "### User request" in card
    assert "### Assistant outcome" in card
    assert "I found the relevant memory." in card
    assert "### Conversation signals" in card
    assert "- Role counts: assistant:1, tool:1, user:1" in card
    assert "- Notable message types: assistant, tool, user" in card
    assert "OPENAI_API_KEY=[REDACTED]" in card
    assert "abc123456789" not in card
    assert "large raw payload that should not be dumped" not in card


def test_gemini_card_is_graphiti_candidate_report_eligible(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    output = tmp_path / "cards"
    write_session(transcript)
    conversation = parse_gemini_chat(transcript, machine="Test Mac")
    write_gemini_cards([conversation], output, machine="Test Mac")
    card = output / "memory" / "antigravity" / "gemini_cli" / "2026-06.md"

    report = build_candidate_report([card])

    assert report.rejected == []
    assert len(report.accepted) == 1
    assert report.accepted[0].source == card


def test_gemini_card_removes_injected_hook_context_from_excerpts(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    write_session(transcript)
    payload = json.loads(transcript.read_text(encoding="utf-8"))
    payload["messages"][0]["content"] = "Fetch Linear issue MON-451. <hook_context># SOUL\nDo not store this."
    transcript.write_text(json.dumps(payload), encoding="utf-8")
    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    card = render_gemini_session_card(conversation)

    assert "Fetch Linear issue MON-451." in card
    assert "<hook_context>" not in card
    assert "# SOUL" not in card


def test_write_gemini_cards_buckets_by_session_month_and_writes_manifest(tmp_path: Path) -> None:
    may = tmp_path / "session-may.json"
    june = tmp_path / "session-june.json"
    write_session(may, session_id="session-may", started_at="2026-05-31T23:59:00Z")
    write_session(june, session_id="session-june", started_at="2026-06-01T00:01:00Z")
    conversations = [parse_gemini_chat(may, machine="Test Mac"), parse_gemini_chat(june, machine="Test Mac")]
    output = tmp_path / "cards"

    summary = write_gemini_cards(conversations, output, machine="Test Mac")

    may_markdown = output / "memory" / "antigravity" / "gemini_cli" / "2026-05.md"
    june_markdown = output / "memory" / "antigravity" / "gemini_cli" / "2026-06.md"
    manifest_path = output / "card-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert summary["card_count"] == 2
    assert may_markdown.is_file()
    assert june_markdown.is_file()
    assert manifest_path.is_file()
    assert manifest["session_ids"] == ["session-june", "session-may"]
    assert manifest["source_paths"] == [str(june), str(may)]
    assert manifest["card_count"] == 2
    assert manifest["card_format"] == "antigravity_gemini_session_card_v1"
    assert scan_path_for_secrets(output) == []


def test_antigravity_cards_cli_accepts_single_file_input(tmp_path: Path) -> None:
    transcript = tmp_path / "session-1.json"
    output = tmp_path / "cards"
    write_session(transcript)

    result = run_backfill("antigravity-cards", "--input", str(transcript), "--machine", "Test Mac", "--output", str(output))
    payload = json.loads(result.stdout)
    markdown = (output / "memory" / "antigravity" / "gemini_cli" / "2026-06.md").read_text(encoding="utf-8")

    assert payload["card_count"] == 1
    assert "backfill-agent:antigravity" in markdown
    assert json.loads((output / "card-manifest.json").read_text(encoding="utf-8"))["card_count"] == 1


def test_antigravity_cards_cli_directory_input_is_non_recursive(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output = tmp_path / "cards"
    write_session(input_dir / "session-1.json", session_id="session-1")
    write_session(input_dir / "session-2.json", session_id="session-2")
    write_session(input_dir / "nested" / "session-3.json", session_id="session-3")

    result = run_backfill("antigravity-cards", "--input", str(input_dir), "--machine", "Test Mac", "--output", str(output))
    payload = json.loads(result.stdout)
    manifest = json.loads((output / "card-manifest.json").read_text(encoding="utf-8"))
    markdown = (output / "memory" / "antigravity" / "gemini_cli" / "2026-06.md").read_text(encoding="utf-8")

    assert payload["card_count"] == 2
    assert manifest["session_ids"] == ["session-1", "session-2"]
    assert "session:session-1" in markdown
    assert "session:session-2" in markdown
    assert "session:session-3" not in markdown


def test_write_gemini_cards_force_refuses_non_generated_output(tmp_path: Path) -> None:
    transcript = tmp_path / "session-1.json"
    output = tmp_path / "cards"
    output.mkdir()
    (output / "keep.txt").write_text("not generated by the card writer", encoding="utf-8")
    write_session(transcript)
    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    with pytest.raises(FileExistsError, match="refusing to overwrite non-generated output entries"):
        write_gemini_cards([conversation], output, machine="Test Mac", force=True)

    assert (output / "keep.txt").read_text(encoding="utf-8") == "not generated by the card writer"


def test_write_gemini_cards_force_refuses_nested_non_generated_memory_content(tmp_path: Path) -> None:
    transcript = tmp_path / "session-1.json"
    output = tmp_path / "cards"
    user_note = output / "memory" / "notes.md"
    user_note.parent.mkdir(parents=True)
    user_note.write_text("keep this", encoding="utf-8")
    write_session(transcript)
    conversation = parse_gemini_chat(transcript, machine="Test Mac")

    with pytest.raises(FileExistsError, match=r"memory/notes\.md"):
        write_gemini_cards([conversation], output, machine="Test Mac", force=True)

    assert user_note.read_text(encoding="utf-8") == "keep this"


def test_antigravity_cards_cli_empty_directory_fails(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output = tmp_path / "cards"
    input_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "memsearch.backfill.cli",
            "antigravity-cards",
            "--input",
            str(input_dir),
            "--machine",
            "Test Mac",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "no Antigravity JSON files found" in result.stderr
    assert not output.exists()


def test_antigravity_cards_cli_secret_scan_failure_leaves_no_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = tmp_path / "session-1.json"
    output = tmp_path / "cards"
    write_session(transcript)

    def fake_scan_path_for_secrets(path: Path) -> list[object]:
        return [object()]

    monkeypatch.setattr(backfill_cli, "scan_path_for_secrets", fake_scan_path_for_secrets)
    result = CliRunner().invoke(
        backfill_cli.main,
        [
            "antigravity-cards",
            "--input",
            str(transcript),
            "--machine",
            "Test Mac",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert "Antigravity card secret scan found 1 hit(s)" in result.output
    assert not output.exists()
