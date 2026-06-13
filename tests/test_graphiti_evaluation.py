from __future__ import annotations

from memsearch.graphiti.evaluation import DEFAULT_GRAPH_EVALUATION_CASES, GraphEvaluationCase, evaluate_payload


def test_default_cases_cover_current_route_and_negative_controls() -> None:
    cases = {case.name: case for case in DEFAULT_GRAPH_EVALUATION_CASES}

    assert set(cases) >= {
        "relationship-tailscale-current-routing",
        "relationship-mac-mini-current-route",
        "relationship-graphiti-falkordb-mac-mini",
        "negative-nordvpn-meshnet-restart",
        "negative-open-brain-nord-hostnames",
        "negative-stale-mac-mini-ip",
        "negative-retired-graphiti-proxy",
    }
    assert cases["relationship-mac-mini-current-route"].graph_must_contain == (
        "dom-kamet.tailf78a36.ts.net",
        "100.72.169.59",
    )
    assert cases["relationship-branch-graphiti-falkordb"].graph_must_contain == (
        "dom/mon-316-graphiti-falkordb",
        "Graphiti",
        "FalkorDB",
    )
    assert cases["relationship-tailscale-current-routing"].graph_must_contain == (
        "Tailscale",
        "NordVPN",
        "Meshnet",
        "replaced",
        "not part",
    )
    assert cases["relationship-graphiti-falkordb-mac-mini"].graph_must_contain == (
        "Graphiti",
        "FalkorDB",
        "Mac Mini",
        "Tailscale Serve",
    )
    assert "100.87.225.99" not in cases["relationship-tailscale-current-routing"].graph_must_not_contain
    assert ".nord" not in cases["relationship-graphiti-falkordb-mac-mini"].graph_must_not_contain
    assert "should use .nord" in cases["relationship-mac-mini-current-route"].graph_must_not_contain
    assert "restart NordVPN" in cases["negative-nordvpn-meshnet-restart"].graph_must_not_contain
    assert "historical" in cases["negative-stale-mac-mini-ip"].graph_must_contain
    assert "use the tailnet proxy" in cases["negative-retired-graphiti-proxy"].graph_must_not_contain


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
