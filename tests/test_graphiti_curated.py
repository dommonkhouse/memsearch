from __future__ import annotations

from memsearch.graphiti.curated import (
    CURATED_GROUP_ID,
    CURATED_MANIFEST_PATH,
    build_curated_episodes,
    select_curated_paths,
)


def test_curated_selection_keeps_durable_sources_and_excludes_raw_memory(tmp_path):
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "cards" / "memory" / "linear" / "2026-06.md"
    project = tmp_path / "claude-config" / "memory" / "projects" / "memsearch.md"
    raw_daily = tmp_path / ".memsearch" / "memory" / "2026-06-12.md"
    transcript = tmp_path / ".memsearch" / "memory" / "historical-sessions" / "session.md"
    code_dump = tmp_path / "claude-config" / "memory" / "code-dumps" / "dump.md"
    for path in [linear, project, raw_daily, transcript, code_dump]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("### Useful\n\nDurable source content.\n", encoding="utf-8")

    selection = select_curated_paths([linear, project, raw_daily, transcript, code_dump])

    assert selection.selected == [linear, project]
    assert selection.excluded == [raw_daily, transcript, code_dump]


def test_curated_episode_builder_uses_selected_files_only(tmp_path):
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "2026-06.md"
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-12.md"
    linear.parent.mkdir(parents=True, exist_ok=True)
    raw.parent.mkdir(parents=True, exist_ok=True)
    linear.write_text("### MON-316\n\nGraphiti relates MON-316 to FalkorDB.\n", encoding="utf-8")
    raw.write_text("### Chat dump\n\nNoisy raw chat.\n", encoding="utf-8")

    episodes, selection = build_curated_episodes([linear, raw])

    assert len(episodes) == 1
    assert "MON-316" in episodes[0].name
    assert episodes[0].metadata["source"] == str(linear)
    assert selection.selected == [linear]
    assert CURATED_GROUP_ID == "ms_memsearch_active_curated_v1"
    assert CURATED_MANIFEST_PATH == ".memsearch/graphiti-curated-manifest.json"


def test_curated_selection_keeps_repo_tracked_seed_files(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "2026-06-13-mon316.md"
    seed.parent.mkdir(parents=True)
    seed.write_text("### MON-316 relationship\n\nGraphiti relates to FalkorDB.\n", encoding="utf-8")

    episodes, selection = build_curated_episodes([seed])

    assert selection.selected == [seed]
    assert len(episodes) == 1
    assert episodes[0].metadata["source"] == str(seed)
