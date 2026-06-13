"""Rank and filter Graphiti search results for opt-in MemSearch recall."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*")
_LOW_SIGNAL_TERMS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "before",
    "between",
    "by",
    "change",
    "changed",
    "connect",
    "connected",
    "connection",
    "does",
    "did",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "relate",
    "relates",
    "relationship",
    "relationships",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def tune_graph_results(
    query: str,
    facts: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    *,
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    """Return query-relevant, non-expired Graphiti facts and de-duplicated nodes.

    The graph lane is still explicitly separate from vector search. This tuning
    only makes the opt-in graph section less noisy.
    """
    terms = _query_terms(query)
    ranked_facts = _rank_facts(terms, facts)
    ranked_nodes = _rank_nodes(terms, nodes)
    return {"facts": ranked_facts[:limit], "nodes": ranked_nodes[:limit]}


def select_graph_center_nodes(query: str, nodes: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    """Pick Graphiti nodes worth using as centred fact-search anchors."""
    terms = _query_terms(query)
    ranked_nodes = _rank_nodes(terms, nodes)
    anchors = _anchor_terms(terms)
    if anchors:
        ranked_nodes = [node for node in ranked_nodes if _score_text(anchors, _node_text(node))]
    return [node for node in ranked_nodes if node.get("uuid")][:limit]


def dedupe_graph_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove repeated facts when uncentred and centred Graphiti searches overlap."""
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fact in facts:
        key = str(fact.get("uuid") or fact.get("fact") or fact).casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped


def _query_terms(query: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(query.lower()) if token not in _LOW_SIGNAL_TERMS and len(token) > 1}


def _anchor_terms(terms: set[str]) -> set[str]:
    return {term for term in terms if any(char in term for char in "-_/") or any(char.isdigit() for char in term)}


def _rank_facts(terms: set[str], facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, fact in enumerate(facts):
        if fact.get("expired_at") or fact.get("invalid_at"):
            continue
        score = _score_text(terms, _fact_text(fact))
        if terms and score == 0:
            continue
        ranked.append((score, -index, {**fact, "graph_score": score}))
    ranked.sort(reverse=True)
    return [fact for _, _, fact in ranked]


def _rank_nodes(terms: set[str], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_name: dict[str, tuple[int, int, dict[str, Any]]] = {}
    for index, node in enumerate(nodes):
        score = _score_text(terms, _node_text(node))
        if terms and score == 0:
            continue
        key = str(node.get("name") or node.get("uuid") or index).casefold()
        candidate = (score, -index, {**node, "graph_score": score})
        if key not in best_by_name or candidate > best_by_name[key]:
            best_by_name[key] = candidate
    return [node for _, _, node in sorted(best_by_name.values(), reverse=True)]


def _score_text(terms: set[str], text: str) -> int:
    lowered = text.lower()
    text_terms = set(_TOKEN_RE.findall(lowered))
    score = 0
    for term in terms:
        if term in text_terms:
            score += _term_weight(term)
        elif len(term) >= 4 and term in lowered:
            score += 1
    return score


def _term_weight(term: str) -> int:
    if any(char in term for char in "-_/") or any(char.isdigit() for char in term):
        return 4
    return 2 if len(term) >= 8 else 1


def _fact_text(fact: dict[str, Any]) -> str:
    return " ".join(str(fact.get(field, "")) for field in ("fact", "name"))


def _node_text(node: dict[str, Any]) -> str:
    return " ".join(str(node.get(field, "")) for field in ("name", "summary"))
