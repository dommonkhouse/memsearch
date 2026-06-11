"""Build deterministic Graphiti episodes from Markdown memory files."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memsearch.chunker import chunk_markdown


@dataclass(frozen=True)
class GraphitiEpisode:
    name: str
    body: str
    source_description: str
    reference_time: str | None
    metadata: dict[str, Any]
    content_hash: str


def build_episodes(paths: Iterable[Path | str]) -> Iterator[GraphitiEpisode]:
    """Yield one Graphiti episode per meaningful Markdown section."""
    for raw_path in paths:
        path = Path(raw_path)
        text = path.read_text(encoding="utf-8")
        for chunk in chunk_markdown(text, source=str(path)):
            yield GraphitiEpisode(
                name=_episode_name(path, chunk.heading, chunk.start_line),
                body=chunk.content,
                source_description="memsearch markdown memory",
                reference_time=_reference_time(path, chunk.heading),
                metadata={
                    "source": str(path),
                    "heading": chunk.heading,
                    "heading_level": chunk.heading_level,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                },
                content_hash=chunk.content_hash,
            )


def _episode_name(path: Path, heading: str, start_line: int) -> str:
    suffix = heading or f"line-{start_line}"
    return f"{path.name}:{suffix}"


def _reference_time(path: Path, heading: str) -> str | None:
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not date_match:
        return None

    time_match = re.match(r"(\d{2}:\d{2})\b", heading)
    if not time_match:
        return date_match.group(1)

    return f"{date_match.group(1)}T{time_match.group(1)}:00"
