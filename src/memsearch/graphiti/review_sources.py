"""Reviewed source selection for Graphiti freshness worklists."""

from __future__ import annotations

from pathlib import Path

MEMORY_ROOT = Path("/Users/dominicmonkhouse/Projects/claude-config/memory")
PROJECTS_ROOT = Path("/Users/dominicmonkhouse/Projects")
MEMSEARCH_ROOT = Path("/Users/dominicmonkhouse/Projects/memsearch")

REVIEWED_MEMORY_DIRS = (
    MEMORY_ROOT / "global",
    MEMORY_ROOT / "tools",
    MEMORY_ROOT / "projects",
    MEMORY_ROOT / "bugs",
    MEMORY_ROOT / "user",
)

EXCLUDED_ROOT_MARKDOWN = {"MEMORY.md", "README.md"}

BLOCKED_SOURCE_PATHS = (
    MEMORY_ROOT / "feedback",
    MEMORY_ROOT / "agent-captures",
    PROJECTS_ROOT / ".memsearch" / "memory" / "linear",
    MEMSEARCH_ROOT / "docs" / "graphiti-curated-seeds",
)


def existing_review_source_paths() -> list[Path]:
    """Return the reviewed memory roots/files used for Graphiti freshness review."""
    candidates: list[Path] = []
    candidates.extend(path for path in REVIEWED_MEMORY_DIRS if path.exists())
    if MEMORY_ROOT.exists():
        candidates.extend(
            path
            for path in MEMORY_ROOT.glob("*.md")
            if path.name not in EXCLUDED_ROOT_MARKDOWN and not path.name.startswith("feedback_")
        )
    return sorted(path for path in candidates if path.exists() and not is_blocked_source_path(path))


def is_blocked_source_path(path: Path) -> bool:
    """Return true when a source path is outside the reviewed Graphiti worklist scope."""
    resolved = path.expanduser().resolve(strict=False)
    if resolved.name == "README.md" or resolved.name.startswith("feedback_"):
        return True
    return any(_is_relative_to(resolved, blocked.expanduser().resolve(strict=False)) for blocked in BLOCKED_SOURCE_PATHS)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
