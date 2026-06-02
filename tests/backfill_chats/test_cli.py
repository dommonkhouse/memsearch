from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


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


def test_inventory_cli_emits_json_counts(tmp_path: Path) -> None:
    write_jsonl(tmp_path / ".claude/projects/foo/session.jsonl", [{"type": "user", "message": {"content": "Hello"}}])
    write_jsonl(
        tmp_path / ".codex/sessions/2026/06/01/rollout.jsonl",
        [{"type": "event_msg", "payload": {"type": "user_message", "message": "Hello"}}],
    )

    result = run_backfill("inventory", "--home", str(tmp_path), "--machine", "Test Mac", "--json-output")
    payload = json.loads(result.stdout)

    assert payload["machine"] == "Test Mac"
    assert payload["counts"] == {"claude_code": 1, "codex": 1}


def test_pilot_cli_writes_markdown_and_manifest_without_duplicates(tmp_path: Path) -> None:
    home = tmp_path / "home"
    output = tmp_path / "pilot"
    write_jsonl(
        home / ".codex/sessions/2026/06/01/rollout.jsonl",
        [
            {"timestamp": "2026-06-01T10:00:00Z", "type": "session_meta", "payload": {"id": "codex-1"}},
            {"timestamp": "2026-06-01T10:00:01Z", "type": "event_msg", "payload": {"type": "user_message", "message": "Hello"}},
            {
                "timestamp": "2026-06-01T10:00:02Z",
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "World"},
            },
        ],
    )

    first = run_backfill("pilot", "--home", str(home), "--machine", "Test Mac", "--limit", "2", "--output", str(output))
    manifest = output / "manifest-test-mac.json"
    markdown = output / "test-mac/codex/2026-06.md"
    first_manifest = manifest.read_text(encoding="utf-8")
    first_markdown = markdown.read_text(encoding="utf-8")
    second = run_backfill("pilot", "--home", str(home), "--machine", "Test Mac", "--limit", "2", "--output", str(output))

    assert json.loads(first.stdout)["converted"] == 1
    assert json.loads(second.stdout)["converted"] == 0
    assert manifest.read_text(encoding="utf-8") == first_manifest
    assert markdown.read_text(encoding="utf-8") == first_markdown
    assert first_markdown.count("backfill-agent:codex") == 1


def test_convert_cli_is_byte_identical_on_second_run(tmp_path: Path) -> None:
    home = tmp_path / "home"
    output = tmp_path / "imported"
    write_jsonl(
        home / ".claude/projects/foo/session.jsonl",
        [
            {
                "timestamp": "2026-06-01T10:00:01Z",
                "type": "user",
                "sessionId": "claude-1",
                "message": {"content": "Remember this"},
            },
            {
                "timestamp": "2026-06-01T10:00:02Z",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Remembered."}]},
            },
        ],
    )

    run_backfill("convert", "--home", str(home), "--machine", "Test Mac", "--output", str(output))
    before = {path.relative_to(output): path.read_text(encoding="utf-8") for path in sorted(output.rglob("*")) if path.is_file()}
    run_backfill("convert", "--home", str(home), "--machine", "Test Mac", "--output", str(output))
    after = {path.relative_to(output): path.read_text(encoding="utf-8") for path in sorted(output.rglob("*")) if path.is_file()}

    assert before
    assert after == before
