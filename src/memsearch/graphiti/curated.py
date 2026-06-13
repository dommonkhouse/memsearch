"""Curated Graphiti ingestion rules for durable MemSearch memory."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .episodes import GraphitiEpisode, build_episodes

CURATED_GROUP_ID = "ms_memsearch_active_curated_v1"
CURATED_MANIFEST_PATH = ".memsearch/graphiti-curated-manifest.json"

_EXCLUDED_PARTS = {
    "raw",
    "raw-chats",
    "chat-dumps",
    "transcripts",
    "transcript-dumps",
    "imported-sessions",
    "historical-sessions",
    "sessions",
    "metadata",
    "code-dumps",
}
_SUMMARY_PARTS = {"memory", "projects", "tools", "feedback", "bugs", "global", "user", "wordpress"}
_STATUS_FILES = {"project.md", "projects.md", "status.md", "statuses.md", "memory.md", "user.md"}


@dataclass(frozen=True)
class CuratedSelection:
    selected: list[Path]
    excluded: list[Path]


def select_curated_paths(paths: Iterable[Path | str]) -> CuratedSelection:
    """Split markdown paths into curated durable sources and exclusions."""
    selected: list[Path] = []
    excluded: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if is_curated_source(path):
            selected.append(path)
        else:
            excluded.append(path)
    return CuratedSelection(selected=selected, excluded=excluded)


def is_curated_source(path: Path) -> bool:
    """Return True when *path* is durable enough for graph ingestion."""
    if path.suffix.lower() not in {".md", ".markdown"}:
        return False

    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if lowered_parts & _EXCLUDED_PARTS:
        return False
    if name.endswith((".json.md", ".jsonl.md")):
        return False

    # Linear cards are already structured notes, not raw chat transcripts.
    if "linear" in lowered_parts and "memory" in lowered_parts:
        return True

    # Project/status/user summaries are intentionally maintained durable files.
    if name in _STATUS_FILES:
        return True

    # Repo-tracked seed files make hand-curated relationship episodes
    # reproducible without tracking ignored Graphiti runtime state.
    parts_text = "/".join(part.lower() for part in path.parts)
    if "docs/graphiti-curated-seeds" in parts_text:
        return True

    # The canonical claude-config memory tree contains curated summaries and
    # workflow notes. Top-level .memsearch daily files are intentionally omitted.
    return bool("claude-config/memory" in parts_text and lowered_parts & _SUMMARY_PARTS)


def build_curated_episodes(paths: Iterable[Path | str]) -> tuple[list[GraphitiEpisode], CuratedSelection]:
    """Build Graphiti episodes only from selected curated sources."""
    selection = select_curated_paths(paths)
    return list(build_episodes(selection.selected)), selection
