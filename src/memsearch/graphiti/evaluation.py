"""Small evaluation helpers for opt-in Graphiti recall."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphEvaluationCase:
    name: str
    kind: str
    query: str
    vector_must_contain: tuple[str, ...] = ()
    graph_must_contain: tuple[str, ...] = ()
    graph_must_not_contain: tuple[str, ...] = ()


DEFAULT_GRAPH_EVALUATION_CASES = (
    GraphEvaluationCase(
        name="exact-mon-316",
        kind="exact",
        query="MON-316",
        vector_must_contain=("MON-316",),
    ),
    GraphEvaluationCase(
        name="exact-mon-259",
        kind="exact",
        query="MON-259",
        vector_must_contain=("MON-259",),
    ),
    GraphEvaluationCase(
        name="exact-branch",
        kind="exact",
        query="dom/mon-316-graphiti-falkordb",
        vector_must_contain=("dom/mon-316-graphiti-falkordb",),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-falkordb-mon316",
        kind="relationship",
        query="How does Graphiti relate to FalkorDB and Tailscale Serve in MON-316?",
        vector_must_contain=("MON-316",),
        graph_must_contain=("Graphiti", "FalkorDB", "Tailscale Serve"),
    ),
    GraphEvaluationCase(
        name="relationship-branch-graphiti-falkordb",
        kind="relationship",
        query="How is dom/mon-316-graphiti-falkordb connected to Graphiti and FalkorDB?",
        vector_must_contain=("dom/mon-316-graphiti-falkordb",),
        graph_must_contain=("dom/mon-316-graphiti-falkordb", "Graphiti"),
    ),
    GraphEvaluationCase(
        name="negative-mon-249-performance",
        kind="negative",
        query="MON-249 homepage performance recovery",
        graph_must_not_contain=("Graphiti", "FalkorDB"),
    ),
    GraphEvaluationCase(
        name="negative-generic-relationship-word",
        kind="negative",
        query="What is the relationship between MON-249 and homepage performance?",
        graph_must_not_contain=("Relationship Type",),
    ),
)


def evaluate_payload(case: GraphEvaluationCase, payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one vector+graph payload against a lightweight control case."""
    vector_text = _stringify(payload.get("vector", []))
    graph_text = _stringify(payload.get("graph", {}))
    vector_hits = _hits(vector_text, case.vector_must_contain)
    graph_hits = _hits(graph_text, case.graph_must_contain)
    graph_unwanted_hits = _hits(graph_text, case.graph_must_not_contain)
    passed = (
        len(vector_hits) == len(case.vector_must_contain)
        and len(graph_hits) == len(case.graph_must_contain)
        and not graph_unwanted_hits
        and not payload.get("graph_error")
    )
    return {
        "name": case.name,
        "kind": case.kind,
        "query": case.query,
        "passed": passed,
        "vector_hits": vector_hits,
        "graph_hits": graph_hits,
        "graph_unwanted_hits": graph_unwanted_hits,
        "graph_fact_count": len(payload.get("graph", {}).get("facts", [])),
        "graph_node_count": len(payload.get("graph", {}).get("nodes", [])),
        "graph_error": payload.get("graph_error"),
    }


def _hits(text: str, needles: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [needle for needle in needles if needle.casefold() in lowered]


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    return str(value)
