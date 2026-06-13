from __future__ import annotations

from memsearch.graphiti.results import dedupe_graph_facts, select_graph_center_nodes, tune_graph_results


def test_tune_graph_results_filters_expired_facts_and_ranks_query_matches() -> None:
    result = tune_graph_results(
        "How does Graphiti relate to FalkorDB and Tailscale Serve in MON-316?",
        [
            {"fact": "MON-310 owns unrelated CMM taxonomy cleanup."},
            {
                "fact": "Graphiti will be checked with ruff during the plan execution.",
                "expired_at": "2026-06-12T22:02:37.045366Z",
                "invalid_at": "2026-06-11T10:23:41.342000Z",
            },
            {"fact": "Graphiti and FalkorDB are an optional derived knowledge-graph layer in MON-316."},
        ],
        [
            {"name": "MON-310", "summary": "CMM taxonomy cleanup."},
            {"name": "Graphiti", "summary": "Temporal memory graph for MON-316."},
            {"name": "Graphiti", "summary": "Duplicate lower quality node."},
            {"name": "FalkorDB", "summary": "Graph database used by Graphiti."},
        ],
        limit=5,
    )

    assert [fact["fact"] for fact in result["facts"]] == [
        "Graphiti and FalkorDB are an optional derived knowledge-graph layer in MON-316."
    ]
    assert [node["name"] for node in result["nodes"]] == ["Graphiti", "FalkorDB"]


def test_tune_graph_results_keeps_negative_control_empty_for_unrelated_graph_hits() -> None:
    result = tune_graph_results(
        "MON-249 homepage performance recovery",
        [{"fact": "Graphiti is being added as a memory graph layer."}],
        [{"name": "FalkorDB", "summary": "Graph database used by Graphiti."}],
        limit=5,
    )

    assert result == {"facts": [], "nodes": []}


def test_tune_graph_results_ignores_generic_relationship_word() -> None:
    result = tune_graph_results(
        "What is the relationship between MON-316 and MON-310?",
        [{"fact": "Relationship Type has 125 contacts populated among the custom fields."}],
        [{"name": "Relationship Type", "summary": "CRM field metadata."}],
        limit=5,
    )

    assert result == {"facts": [], "nodes": []}


def test_select_graph_center_nodes_prefers_identifier_anchors() -> None:
    centers = select_graph_center_nodes(
        "What changed in MON-316 after the Graphiti Mac Mini deployment?",
        [
            {"name": "Mac Mini", "uuid": "generic", "summary": "Dominic used a Mac Mini for unrelated work."},
            {"name": "MON-316", "uuid": "issue", "summary": "Graphiti FalkorDB memory layer."},
        ],
        limit=2,
    )

    assert [node["uuid"] for node in centers] == ["issue"]


def test_dedupe_graph_facts_removes_overlapping_centered_results() -> None:
    facts = dedupe_graph_facts(
        [
            {"uuid": "1", "fact": "Graphiti is backed by FalkorDB."},
            {"uuid": "1", "fact": "Graphiti is backed by FalkorDB.", "graph_center_node": "Graphiti"},
            {"fact": "MON-316 uses Graphiti."},
            {"fact": "MON-316 uses Graphiti.", "graph_center_node": "MON-316"},
        ]
    )

    assert facts == [
        {"uuid": "1", "fact": "Graphiti is backed by FalkorDB."},
        {"fact": "MON-316 uses Graphiti."},
    ]
