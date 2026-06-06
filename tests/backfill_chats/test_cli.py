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


def test_pilot_limit_applies_per_product(tmp_path: Path) -> None:
    home = tmp_path / "home"
    output = tmp_path / "pilot"
    for idx in range(2):
        write_jsonl(
            home / f".claude/projects/foo/session-{idx}.jsonl",
            [
                {
                    "timestamp": "2026-06-01T10:00:01Z",
                    "type": "user",
                    "sessionId": f"claude-{idx}",
                    "message": {"content": f"Claude {idx}"},
                }
            ],
        )
        write_jsonl(
            home / f".codex/sessions/2026/06/01/rollout-{idx}.jsonl",
            [
                {"timestamp": "2026-06-01T10:00:00Z", "type": "session_meta", "payload": {"id": f"codex-{idx}"}},
                {
                    "timestamp": "2026-06-01T10:00:01Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": f"Codex {idx}"},
                },
            ],
        )

    result = run_backfill("pilot", "--home", str(home), "--machine", "Test Mac", "--limit", "1", "--output", str(output))
    payload = json.loads(result.stdout)

    assert payload["converted"] == 2


def test_scan_secrets_cli_returns_nonzero_on_hits(tmp_path: Path) -> None:
    target = tmp_path / "run"
    target.mkdir()
    (target / "manifest.json").write_text('{"secret":"OPENAI_API_KEY=abc123456789"}', encoding="utf-8")

    env = os.environ.copy()
    env.pop("MEMSEARCH_DIR", None)
    result = subprocess.run(
        [sys.executable, "-m", "memsearch.backfill.cli", "scan-secrets", str(target)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "manifest.json" in result.stdout


def test_manus_mark_not_indexed_cli_writes_reason_note(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()

    result = run_backfill("manus-mark-not-indexed", str(run_dir), "--reason", "checksum mismatch")
    payload = json.loads(result.stdout)
    note = Path(payload["note_path"]).read_text(encoding="utf-8")

    assert "checksum mismatch" in note
    assert "must not be passed to MemSearch indexing" in note


def test_manus_cards_cli_writes_card_lane(tmp_path: Path) -> None:
    promoted = tmp_path / "promoted"
    markdown_root = promoted / "memory" / "manus_cloud" / "manus_api"
    markdown_root.mkdir(parents=True)
    (markdown_root / "2026-01.md").write_text(
        "\n".join(
            [
                "## Manus Api session 2026-01-01T00:00:00+00:00: Test task",
                "<!-- backfill-agent:manus_api task:task-cli source:manus_api exported_by_machine:manus-cloud -->",
                "",
                "- Manus task ID: task-cli",
                "- Manus task URL: https://manus.im/app/task-cli",
                "- Time range: 2026-01-01T00:00:00+00:00 to 2026-01-01T00:01:00+00:00",
                "- Manus status: stopped",
                "- Manus message events: 3",
                "- Manus artefacts: 0",
                "",
                "### User 1780000000000",
                "",
                "Find the podcast transcript",
                "",
                "### Assistant 1780000001000",
                "",
                "I found the transcript.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "cards"

    result = run_backfill("manus-cards", "--promoted", str(promoted), "--output", str(output))
    payload = json.loads(result.stdout)
    card_markdown = (output / "memory" / "manus_cloud" / "manus_api" / "2026-01.md").read_text(encoding="utf-8")

    assert payload["task_cards"] == 1
    assert payload["unique_task_ids"] == 1
    assert payload["markdown_files"] == 1
    assert "Find the podcast transcript" in card_markdown
    assert "I found the transcript." in card_markdown
    assert "Full cleaned transcript:" in card_markdown
