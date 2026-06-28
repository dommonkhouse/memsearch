from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .indexing import search_proof
from .source_state import read_source_state


@dataclass(frozen=True)
class SourceFreshness:
    source: str
    last_success_at: str
    last_failure_at: str
    card_count: int
    state_status: str
    next_run: str
    proof_searches: list[dict[str, Any]]

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "card_count": self.card_count,
            "state_status": self.state_status,
            "next_run": self.next_run,
            "proof_searches": self.proof_searches,
        }


def source_freshness_report(
    *,
    state_dir: Path = Path(".local/source-sync-state"),
    memory_root: Path = Path("/Users/dominicmonkhouse/Projects/.memsearch/memory"),
    collection: str = "memsearch_chunks",
    run_proof: bool = False,
) -> dict[str, Any]:
    sources = [
        _source_report("linear", state_dir=state_dir, memory_root=memory_root, collection=collection, run_proof=run_proof),
        _source_report("manus", state_dir=state_dir, memory_root=memory_root, collection=collection, run_proof=run_proof),
        _source_report("antigravity", state_dir=state_dir, memory_root=memory_root, collection=collection, run_proof=run_proof),
    ]
    return {
        "sources": [source.to_json() for source in sources],
        "memsearch": {
            "collection": collection,
            "row_count_status": "not_checked_by_default",
            "row_count_reason": "freshness report is safe/read-only unless proof search execution is explicitly requested",
        },
    }


def source_freshness_json(**kwargs: Any) -> str:
    return json.dumps(source_freshness_report(**kwargs), indent=2, sort_keys=True)


def _source_report(
    source: str,
    *,
    state_dir: Path,
    memory_root: Path,
    collection: str,
    run_proof: bool,
) -> SourceFreshness:
    state = read_source_state(state_dir, source)
    card_root = _card_root(source, memory_root)
    proof_searches: list[dict[str, Any]] = []
    for proof_id in state.proof_ids[:3]:
        result = search_proof(proof_id, collection=collection, dry_run=not run_proof)
        proof_searches.append(
            {
                "query": proof_id,
                "command": result.command,
                "status": "preview" if result.skipped else "ran",
                "returncode": result.returncode,
            }
        )
    if not proof_searches:
        proof_searches.append({"query": "", "command": [], "status": "missing-proof-id", "returncode": 0})
    return SourceFreshness(
        source=source,
        last_success_at=state.last_success_at,
        last_failure_at=state.last_failure_at,
        card_count=_count_markdown_cards(card_root),
        state_status="present" if (state_dir / f"{source}.json").is_file() else "missing-state",
        next_run=_next_run(source),
        proof_searches=proof_searches,
    )


def _card_root(source: str, memory_root: Path) -> Path:
    if source == "linear":
        return memory_root / "linear"
    if source == "manus":
        return memory_root / "manus-cloud" / "manus-api"
    if source == "antigravity":
        return memory_root / "antigravity" / "gemini-cli"
    raise ValueError(f"Unsupported source: {source}")


def _next_run(source: str) -> str:
    if source == "linear":
        return "daily at 06:30 local"
    if source == "manus":
        return "weekly Monday at 06:00 local"
    if source == "antigravity":
        return "daily at 06:40 local"
    raise ValueError(f"Unsupported source: {source}")


def _count_markdown_cards(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*.md") if item.is_file())
