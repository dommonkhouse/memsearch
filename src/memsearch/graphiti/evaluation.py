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
        graph_must_contain=("dom/mon-316-graphiti-falkordb", "Graphiti", "FalkorDB"),
    ),
    GraphEvaluationCase(
        name="relationship-tailscale-current-routing",
        kind="relationship",
        query="Is NordVPN still used or is this Tailscale only?",
        graph_must_contain=("Tailscale", "NordVPN", "Meshnet", "replaced", "not part"),
        graph_must_not_contain=(
            "restart NordVPN",
            "restart Meshnet",
            "should use NordVPN",
            "should use Meshnet",
            "should use .nord",
            "use .nord",
            "use 100.87.225.99",
            "100.87.225.99 is current",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-mac-mini-current-route",
        kind="relationship",
        query="What host should I use for the Mac Mini now NordVPN Meshnet is retired?",
        graph_must_contain=("dom-kamet.tailf78a36.ts.net", "100.72.169.59"),
        graph_must_not_contain=("should use .nord", "use 100.87.225.99", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-falkordb-mac-mini",
        kind="relationship",
        query="How does Graphiti reach FalkorDB on the Mac Mini through Tailscale Serve?",
        graph_must_contain=("Graphiti", "FalkorDB", "Mac Mini", "Tailscale Serve"),
        graph_must_not_contain=("should use .nord", "use 100.87.225.99", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="relationship-memory-recall-codex-claude",
        kind="relationship",
        query="How does memory recall differ between Codex and Claude Code?",
        graph_must_contain=("Codex", "main conversation context", "Claude Code", "forked subagent"),
        graph_must_not_contain=("Codex uses a forked subagent",),
    ),
    GraphEvaluationCase(
        name="relationship-memory-recall-layers",
        kind="relationship",
        query="What are the L1 L2 and L3 layers in MemSearch memory recall?",
        graph_must_contain=("L1 search", "L2 expand", "L3 transcript"),
    ),
    GraphEvaluationCase(
        name="relationship-memsearch-hybrid-identifiers",
        kind="relationship",
        query="Why does MemSearch help with exact identifiers compared with dense-only memory search?",
        graph_must_contain=("BM25", "exact identifiers", "dense"),
    ),
    GraphEvaluationCase(
        name="relationship-open-brain-advisory-guardrails",
        kind="relationship",
        query="What relationship edges should Open Brain avoid inferring from advisory conversations?",
        graph_must_contain=("advisory patterns", "client_of", "works_on", "stronger evidence"),
        graph_must_not_contain=("Dominic works_on salon owners", "Dominic client_of salon owners"),
    ),
    GraphEvaluationCase(
        name="relationship-source-freshness-cadence",
        kind="relationship",
        query="What is the source freshness cadence for Linear and Manus?",
        graph_must_contain=("Linear", "daily", "Manus", "weekly"),
    ),
    GraphEvaluationCase(
        name="relationship-manus-card-safety-lane",
        kind="relationship",
        query="Why are Manus cards the practical MemSearch indexing source instead of raw exports?",
        graph_must_contain=("Manus", "card lane", "raw exports", "not MemSearch-ready"),
        graph_must_not_contain=("index raw Manus exports",),
    ),
    GraphEvaluationCase(
        name="relationship-linear-source-sync",
        kind="relationship",
        query="How does Linear source sync work for MemSearch freshness?",
        graph_must_contain=("Linear", "read-only GraphQL", "last_success_at", "dry-run previews"),
    ),
    GraphEvaluationCase(
        name="relationship-secret-scan-gates",
        kind="relationship",
        query="What secret scan gates protect Manus source sync before indexing?",
        graph_must_contain=("scan raw output", "scan promoted output", "scan cards", "index"),
    ),
    GraphEvaluationCase(
        name="relationship-platform-capture-shared-memory",
        kind="relationship",
        query="How do MemSearch platform plugins capture memories across Claude Code Codex OpenClaw and OpenCode?",
        graph_must_contain=("Claude Code", "OpenClaw", "OpenCode", "Codex CLI", "daily markdown", "Milvus"),
    ),
    GraphEvaluationCase(
        name="relationship-index-chunk-dedup-flow",
        kind="relationship",
        query="How does MemSearch chunk markdown and deduplicate chunks before indexing?",
        graph_must_contain=("Scanner", "Chunker", "SHA-256", "Milvus", "stale chunks"),
    ),
    GraphEvaluationCase(
        name="relationship-config-priority-chain",
        kind="relationship",
        query="How does MemSearch configuration choose between defaults global project config and CLI flags?",
        graph_must_contain=("built-in defaults", "~/.memsearch/config.toml", ".memsearch.toml", "CLI flags"),
    ),
    GraphEvaluationCase(
        name="relationship-watch-compact-loop",
        kind="relationship",
        query="How does the watcher compact memory and re-index markdown?",
        graph_must_contain=("file watcher", "compact", "daily markdown", "re-index"),
    ),
    GraphEvaluationCase(
        name="relationship-cli-command-roles",
        kind="relationship",
        query="How do CLI commands relate to indexing search expand compact and watch?",
        graph_must_contain=(
            "memsearch index",
            "memsearch search",
            "memsearch expand",
            "memsearch compact",
            "memsearch watch",
        ),
    ),
    GraphEvaluationCase(
        name="negative-api-keys-in-config",
        kind="negative",
        query="Does MemSearch write API keys into config files?",
        graph_must_contain=("API keys", "environment variables", "never writes API keys to config files"),
        graph_must_not_contain=("write API keys to config", "store API keys in config"),
    ),
    GraphEvaluationCase(
        name="negative-milvus-source-of-truth",
        kind="negative",
        query="Is Milvus the source of truth for MemSearch memories?",
        graph_must_contain=("Markdown", "source of truth", "Milvus", "derived index"),
        graph_must_not_contain=("Milvus is the source of truth",),
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
    GraphEvaluationCase(
        name="negative-nordvpn-meshnet-restart",
        kind="negative",
        query="Should I restart NordVPN Meshnet to fix MemSearch?",
        graph_must_not_contain=(
            "restart NordVPN",
            "restart Meshnet",
            "should use .nord",
            "use 100.87.225.99",
            "100.87.225.99 is current",
        ),
    ),
    GraphEvaluationCase(
        name="negative-open-brain-nord-hostnames",
        kind="negative",
        query="Should I use .nord hostnames for Open Brain now?",
        graph_must_contain=("not use .nord",),
        graph_must_not_contain=("should use .nord", "dom-kamet.nord is current", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="negative-stale-mac-mini-ip",
        kind="negative",
        query="Is 100.87.225.99 the current Mac Mini route?",
        graph_must_contain=("100.87.225.99", "historical", "stale"),
        graph_must_not_contain=("100.87.225.99 is current", "uses 100.87.225.99"),
    ),
    GraphEvaluationCase(
        name="negative-retired-graphiti-proxy",
        kind="negative",
        query="Should Graphiti tailnet access use the retired tailnet proxy LaunchAgent or old SSH-forward route?",
        graph_must_not_contain=("use the tailnet proxy", "use SSH-forward", "use ssh forward", "should use .nord"),
    ),
    GraphEvaluationCase(
        name="negative-codex-forked-memory-recall",
        kind="negative",
        query="Does Codex memory-recall run inside a forked subagent?",
        graph_must_contain=("Codex", "main conversation context"),
        graph_must_not_contain=("Codex uses a forked subagent", "Codex memory-recall uses a forked subagent"),
    ),
    GraphEvaluationCase(
        name="negative-index-raw-manus-exports",
        kind="negative",
        query="Should MemSearch index raw Manus exports directly?",
        graph_must_contain=("Manus raw exports", "not MemSearch-ready"),
        graph_must_not_contain=("index raw Manus exports", "raw Manus exports should be indexed"),
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
