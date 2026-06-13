from __future__ import annotations

from memsearch.graphiti.evaluation import GraphEvaluationCase, evaluate_payload


def test_evaluate_payload_checks_vector_graph_and_negative_controls() -> None:
    case = GraphEvaluationCase(
        name="relationship",
        kind="relationship",
        query="How does Graphiti relate to FalkorDB in MON-316?",
        vector_must_contain=("MON-316",),
        graph_must_contain=("Graphiti", "FalkorDB"),
        graph_must_not_contain=("MON-310",),
    )

    result = evaluate_payload(
        case,
        {
            "vector": [{"heading": "MON-316", "content": "Graphiti FalkorDB plan"}],
            "graph": {
                "facts": [{"fact": "Graphiti is backed by FalkorDB."}],
                "nodes": [{"name": "Graphiti"}],
            },
        },
    )

    assert result["passed"] is True
    assert result["vector_hits"] == ["MON-316"]
    assert result["graph_hits"] == ["Graphiti", "FalkorDB"]
    assert result["graph_unwanted_hits"] == []


def test_evaluate_payload_fails_when_graph_has_unwanted_hits() -> None:
    case = GraphEvaluationCase(
        name="negative",
        kind="negative",
        query="MON-249 homepage performance recovery",
        vector_must_contain=("MON-249",),
        graph_must_not_contain=("Graphiti",),
    )

    result = evaluate_payload(
        case,
        {
            "vector": [{"heading": "MON-249"}],
            "graph": {"facts": [{"fact": "Graphiti memory layer."}], "nodes": []},
        },
    )

    assert result["passed"] is False
    assert result["graph_unwanted_hits"] == ["Graphiti"]
