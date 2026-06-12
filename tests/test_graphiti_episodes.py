from __future__ import annotations

from memsearch.graphiti.episodes import build_episodes


def test_sections_become_deterministic_episodes(tmp_path):
    memory = tmp_path / "2026-06-11.md"
    memory.write_text(
        "## Session 10:00\n\n"
        "### 10:01\n"
        "<!-- session:abc rollout:/tmp/session.jsonl -->\n"
        "- User asked about Kuzu.\n"
        "- Assistant recommended Graphiti plus FalkorDB.\n",
        encoding="utf-8",
    )

    episodes = list(build_episodes([memory]))

    assert len(episodes) == 1
    assert episodes[0].name.startswith("2026-06-11.md:10:01")
    assert "Graphiti plus FalkorDB" in episodes[0].body
    assert "session:abc" in episodes[0].body
    assert episodes[0].source_description == "memsearch markdown memory"
    assert episodes[0].reference_time == "2026-06-11T10:01:00"
    assert episodes[0].metadata["source"] == str(memory)
    assert episodes[0].metadata["heading"] == "10:01"
    assert episodes[0].metadata["start_line"] > 0
    assert episodes[0].metadata["end_line"] >= episodes[0].metadata["start_line"]
    assert episodes[0].content_hash


def test_episode_hash_is_stable_for_same_content(tmp_path):
    memory = tmp_path / "notes.md"
    memory.write_text("### Decision\n\nUse Graphiti with FalkorDB first.\n", encoding="utf-8")

    first = list(build_episodes([memory]))
    second = list(build_episodes([memory]))

    assert first == second
    assert first[0].content_hash == second[0].content_hash


def test_empty_sections_are_skipped(tmp_path):
    memory = tmp_path / "empty.md"
    memory.write_text(
        "## Empty\n\n"
        "### Metadata only\n"
        "<!-- session:abc rollout:/tmp/session.jsonl -->\n\n"
        "### Useful\n"
        "- Real memory content.\n",
        encoding="utf-8",
    )

    episodes = list(build_episodes([memory]))

    assert len(episodes) == 1
    assert episodes[0].metadata["heading"] == "Useful"


def test_invalid_utf8_bytes_do_not_block_episode_build(tmp_path):
    memory = tmp_path / "2026-06-12.md"
    memory.write_bytes(b"### Bad bytes\n\nUseful memory before bad byte \xff still indexed.\n")

    episodes = list(build_episodes([memory]))

    assert len(episodes) == 1
    assert "Useful memory before bad byte" in episodes[0].body
