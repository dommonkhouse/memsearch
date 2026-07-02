from __future__ import annotations

from memsearch.graphiti import review_sources


def test_existing_review_source_paths_includes_reviewed_dirs_and_root_notes(monkeypatch, tmp_path):
    memory_root = tmp_path / "memory"
    for name in ("global", "tools", "projects", "bugs", "user", "feedback", "agent-captures"):
        (memory_root / name).mkdir(parents=True)
    keeper = memory_root / "keeper.md"
    memory_file = memory_root / "MEMORY.md"
    readme = memory_root / "README.md"
    feedback_note = memory_root / "feedback_example.md"
    for path in (keeper, memory_file, readme, feedback_note):
        path.write_text("memory\n", encoding="utf-8")

    monkeypatch.setattr(review_sources, "MEMORY_ROOT", memory_root)
    monkeypatch.setattr(
        review_sources,
        "REVIEWED_MEMORY_DIRS",
        tuple(memory_root / name for name in ("global", "tools", "projects", "bugs", "user")),
    )
    monkeypatch.setattr(
        review_sources,
        "BLOCKED_SOURCE_PATHS",
        (
            memory_root / "feedback",
            memory_root / "agent-captures",
            tmp_path / ".memsearch" / "memory" / "linear",
            tmp_path / "memsearch" / "docs" / "graphiti-curated-seeds",
        ),
    )

    paths = review_sources.existing_review_source_paths()

    assert paths == sorted(
        [
            memory_root / "bugs",
            memory_root / "global",
            memory_root / "keeper.md",
            memory_root / "projects",
            memory_root / "tools",
            memory_root / "user",
        ]
    )


def test_is_blocked_source_path_rejects_known_blocked_sources(monkeypatch, tmp_path):
    memory_root = tmp_path / "memory"
    projects_root = tmp_path / "Projects"
    memsearch_root = projects_root / "memsearch"
    monkeypatch.setattr(
        review_sources,
        "BLOCKED_SOURCE_PATHS",
        (
            memory_root / "feedback",
            memory_root / "agent-captures",
            projects_root / ".memsearch" / "memory" / "linear",
            memsearch_root / "docs" / "graphiti-curated-seeds",
        ),
    )

    blocked = [
        memory_root / "feedback" / "workflow.md",
        memory_root / "agent-captures" / "capture.md",
        memory_root / "feedback_example.md",
        memory_root / "README.md",
        projects_root / ".memsearch" / "memory" / "linear" / "MON-345.md",
        memsearch_root / "docs" / "graphiti-curated-seeds" / "seed.md",
    ]

    assert all(review_sources.is_blocked_source_path(path) for path in blocked)
    assert not review_sources.is_blocked_source_path(memory_root / "global" / "workflow.md")


def test_existing_review_source_paths_returns_only_existing_sorted_paths(monkeypatch, tmp_path):
    memory_root = tmp_path / "memory"
    existing_b = memory_root / "tools"
    existing_a = memory_root / "global"
    existing_b.mkdir(parents=True)
    existing_a.mkdir(parents=True)
    missing = memory_root / "projects"

    monkeypatch.setattr(review_sources, "MEMORY_ROOT", memory_root)
    monkeypatch.setattr(review_sources, "REVIEWED_MEMORY_DIRS", (existing_b, missing, existing_a))
    monkeypatch.setattr(review_sources, "BLOCKED_SOURCE_PATHS", ())

    assert review_sources.existing_review_source_paths() == [existing_a, existing_b]
