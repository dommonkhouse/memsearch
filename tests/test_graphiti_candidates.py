from __future__ import annotations

from memsearch.graphiti.candidates import CandidateStatus, build_candidate_report


def test_candidate_report_rejects_raw_memory_and_stale_routes(tmp_path):
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-12.md"
    stale_seed = tmp_path / "docs" / "graphiti-curated-seeds" / "stale-route.md"
    raw.parent.mkdir(parents=True)
    stale_seed.parent.mkdir(parents=True)
    raw.write_text("### Old route\n\nUse the historical raw memory export.\n", encoding="utf-8")
    stale_seed.write_text(
        "### Old route\n\nClassification: current\n\nUse .nord hostnames and restart Meshnet.\n\nEvidence: docs/graphiti-falkordb.md\n",
        encoding="utf-8",
    )

    report = build_candidate_report([raw, stale_seed])

    assert report.accepted == []
    assert report.rejected[0].status == CandidateStatus.REJECTED_RAW_SOURCE
    assert any(item.status == CandidateStatus.REJECTED_STALE_ROUTE for item in report.rejected)


def test_candidate_report_accepts_evidence_cited_seed(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "capped-batch-999.md"
    seed.parent.mkdir(parents=True)
    seed.write_text(
        "### Current route\n\nClassification: current\n\nGraphiti MCP is served through Tailscale Serve on port 8018.\n\nEvidence: docs/graphiti-falkordb.md\n",
        encoding="utf-8",
    )

    report = build_candidate_report([seed])

    assert len(report.accepted) == 1
    assert report.accepted[0].source == seed
    assert report.accepted[0].classification == "current"


def test_candidate_report_accepts_antigravity_cards_as_curated_source(tmp_path):
    card = (
        tmp_path
        / ".memsearch"
        / "memory"
        / "antigravity"
        / "gemini-cli"
        / "run-1"
        / "cards"
        / "memory"
        / "antigravity"
        / "gemini_cli"
        / "2026-06.md"
    )
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(
        "### Antigravity session\n\nClassification: current\n\nAntigravity captured a Linear recall proof.\n\nEvidence: card-manifest.json\n",
        encoding="utf-8",
    )

    report = build_candidate_report([card])

    assert len(report.accepted) == 1
    assert report.accepted[0].source == card


def test_candidate_report_requires_classification(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "missing-classification.md"
    seed.parent.mkdir(parents=True)
    seed.write_text("### Route\n\nGraphiti uses Tailscale Serve.\n\nEvidence: docs/graphiti-falkordb.md\n", encoding="utf-8")

    report = build_candidate_report([seed])

    assert report.accepted == []
    assert report.rejected[0].status == CandidateStatus.REJECTED_MISSING_CLASSIFICATION
