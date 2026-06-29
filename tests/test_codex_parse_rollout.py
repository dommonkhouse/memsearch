from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path("plugins/codex/scripts/parse-rollout.sh")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _run_parse(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["bash", str(SCRIPT), *args, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_parse_rollout_omits_tool_output_content(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    _write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Check the journal"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "arguments": json.dumps({"cmd": "tail -80 memory.md"}),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "output": (
                        "Chunk ID: test\n"
                        "Wall time: 0.1234 seconds\n"
                        "Process exited with code 0\n"
                        "Output:\n"
                        "stale fact: memsearch version 0.4.4\n"
                    ),
                },
            },
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Current version is 0.4.5."}},
        ],
    )

    output = _run_parse(rollout)

    assert "[User]: Check the journal" in output
    assert "[Codex calls tool]" not in output
    assert "[Tool output" not in output
    assert "exit_code=0" not in output
    assert "wall_time=0.1234 seconds" not in output
    assert "stale fact" not in output
    assert "0.4.4" not in output
    assert "Current version is 0.4.5." in output


def test_parse_rollout_omits_tool_output_metadata(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    _write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Show output"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "output": "Process exited with code 0\nOutput:\nimportant detail",
                },
            },
        ],
    )

    output = _run_parse(rollout)

    assert "[Tool output" not in output
    assert "exit_code=0" not in output
    assert "important detail" not in output


def test_parse_rollout_omits_tool_error_content(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout-error.jsonl"
    error_text = "prefix " + ("x" * 1200) + " final error marker"
    _write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Debug failure"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "output": f"Process exited with code 2\nOutput:\n{error_text}",
                },
            },
        ],
    )

    output = _run_parse(rollout)

    assert "[Tool output" not in output
    assert "exit_code=2" not in output
    assert "final error marker" not in output
    assert "prefix " not in output


def test_parse_rollout_defaults_to_last_turn(tmp_path: Path) -> None:
    rollout = tmp_path / "multi-turn.jsonl"
    _write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Earlier request"}},
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Earlier answer"}},
            {"type": "event_msg", "payload": {"type": "task_complete"}},
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Final request"}},
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Final answer"}},
        ],
    )

    output = _run_parse(rollout)

    assert "Earlier request" not in output
    assert "Earlier answer" not in output
    assert "[User]: Final request" in output
    assert "[Codex]: Final answer" in output


def test_parse_rollout_all_mode_includes_earlier_turns(tmp_path: Path) -> None:
    rollout = tmp_path / "multi-turn.jsonl"
    _write_jsonl(
        rollout,
        [
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Earlier request"}},
            {
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "Earlier answer"},
            },
            {"type": "event_msg", "payload": {"type": "task_complete"}},
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Unrelated final request"}},
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "Unrelated final answer"}},
        ],
    )

    output = _run_parse(rollout, "--all")

    assert "[User]: Earlier request" in output
    assert "[Codex]: Earlier answer" in output
    assert "[User]: Unrelated final request" in output
    assert "[Codex]: Unrelated final answer" in output
