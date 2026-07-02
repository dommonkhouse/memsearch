from __future__ import annotations

import json

from memsearch.graphiti.candidates import CandidateStatus
from memsearch.graphiti.review_worklist import (
    STATUS_TO_STATE,
    ReportRow,
    build_review_worklist,
    load_review_worklist_json,
    parse_candidate_report,
    render_annotation_sheet_markdown,
    render_review_worklist_json,
    select_annotation_items,
)


def test_parse_candidate_report_handles_real_accepted_and_rejected_shapes(tmp_path):
    accepted = tmp_path / "accepted.md"
    rejected = tmp_path / "rejected.md"
    report = tmp_path / "report.md"
    report.write_text(
        f"""# Graphiti candidate report

## Accepted

No rejected candidates.

- Source: {accepted}
  - Classification: current
  - Status: accepted

## Rejected

No accepted candidates.

- Source: {rejected}
  - Classification: missing
  - Status: rejected_missing_classification
  - Detail: missing Classification marker
""",
        encoding="utf-8",
    )

    rows = parse_candidate_report(report)

    assert rows == [
        ReportRow(source=accepted, section="accepted", classification="current", status="accepted"),
        ReportRow(
            source=rejected,
            section="rejected",
            classification="missing",
            status="rejected_missing_classification",
            detail="missing Classification marker",
        ),
    ]


def test_parse_candidate_report_only_starts_rows_on_source_lines(tmp_path):
    source = tmp_path / "source.md"
    report = tmp_path / "report.md"
    report.write_text(
        f"""# Graphiti candidate report

## Accepted

  - Classification: current
  - Status: accepted

## Rejected

- Detail: missing Classification marker
- Source: {source}
  - Classification: missing
  - Status: rejected_missing_classification
  - Detail: missing Classification marker
""",
        encoding="utf-8",
    )

    assert parse_candidate_report(report) == [
        ReportRow(
            source=source,
            section="rejected",
            classification="missing",
            status="rejected_missing_classification",
            detail="missing Classification marker",
        )
    ]


def test_build_review_worklist_maps_all_current_candidate_statuses(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("Classification: current\nEvidence: docs/example.md\nUseful fact.\n", encoding="utf-8")
    expected = {
        CandidateStatus.ACCEPTED: "seed_ready",
        CandidateStatus.REJECTED_RAW_SOURCE: "blocked_raw_source",
        CandidateStatus.REJECTED_STALE_ROUTE: "stale_route",
        CandidateStatus.REJECTED_MISSING_CLASSIFICATION: "needs_classification",
        CandidateStatus.REJECTED_MISSING_EVIDENCE: "needs_evidence",
        CandidateStatus.REJECTED_NON_CURRENT: "non_current",
        CandidateStatus.REJECTED_UNSAFE: "unsafe",
    }

    rows = [
        ReportRow(
            source=source,
            section="accepted" if status == CandidateStatus.ACCEPTED else "rejected",
            classification="current",
            status=status.value,
        )
        for status in CandidateStatus
    ]

    items = build_review_worklist(rows)

    assert {status.value: state for status, state in expected.items()} == STATUS_TO_STATE
    assert [item.state for item in items] == [expected[status] for status in CandidateStatus]
    assert all(item.excerpt for item in items)


def test_build_review_worklist_handles_unknown_and_missing_sources(tmp_path):
    source = tmp_path / "source.md"
    missing = tmp_path / "missing.md"
    source.write_text("Classification: current\nEvidence: docs/example.md\nUseful fact.\n", encoding="utf-8")

    items = build_review_worklist(
        [
            ReportRow(source=source, section="rejected", classification="current", status="rejected_future_status"),
            ReportRow(source=missing, section="rejected", classification="current", status="accepted"),
        ]
    )

    assert items[0].state == "needs_review"
    assert items[0].source_exists is True
    assert "Useful fact" in items[0].excerpt
    assert items[1].state == "missing_source"
    assert items[1].source_exists is False
    assert items[1].excerpt == ""
    assert items[0].source_fingerprint != items[1].source_fingerprint


def test_render_review_worklist_json_uses_singular_source(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("Classification: current\nEvidence: docs/example.md\nUseful fact.\n", encoding="utf-8")
    item = build_review_worklist(
        [ReportRow(source=source, section="rejected", classification="missing", status="rejected_missing_classification")]
    )[0]

    payload = json.loads(render_review_worklist_json([item], candidate_report=tmp_path / "report.md"))

    assert payload["counts"] == {"needs_classification": 1}
    assert payload["items"][0]["source"] == str(source)
    assert "sources" not in payload["items"][0]


def test_annotation_sheet_selects_items_without_mutating_sources(tmp_path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("First useful fact.\n", encoding="utf-8")
    second.write_text("Second useful fact.\n", encoding="utf-8")
    items = build_review_worklist(
        [
            ReportRow(source=first, section="rejected", classification="missing", status="rejected_missing_classification"),
            ReportRow(source=second, section="rejected", classification="current", status="rejected_missing_evidence"),
        ]
    )
    worklist = tmp_path / "worklist.json"
    worklist.write_text(render_review_worklist_json(items, candidate_report=tmp_path / "report.md"), encoding="utf-8")

    loaded = load_review_worklist_json(worklist)
    selected = select_annotation_items(loaded, states=("needs_classification",), limit=1)
    body = render_annotation_sheet_markdown(selected, worklist_json=worklist)

    assert [item.source for item in selected] == [first]
    assert "Classification: " in body
    assert "Evidence: " in body
    assert "First useful fact." in body
    assert "Second useful fact." not in body
    assert first.read_text(encoding="utf-8") == "First useful fact.\n"
