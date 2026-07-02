"""Local Graphiti freshness review worklist generation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from .candidates import CandidateStatus

EXCERPT_LIMIT = 500


@dataclass(frozen=True)
class ReportRow:
    source: Path
    section: Literal["accepted", "rejected"]
    classification: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class ReviewWorklistItem:
    source: Path
    source_exists: bool
    source_fingerprint: str
    state: str
    classification: str
    status: str
    detail: str
    excerpt: str


STATUS_TO_STATE = {
    CandidateStatus.ACCEPTED.value: "seed_ready",
    CandidateStatus.REJECTED_RAW_SOURCE.value: "blocked_raw_source",
    CandidateStatus.REJECTED_STALE_ROUTE.value: "stale_route",
    CandidateStatus.REJECTED_MISSING_CLASSIFICATION.value: "needs_classification",
    CandidateStatus.REJECTED_MISSING_EVIDENCE.value: "needs_evidence",
    CandidateStatus.REJECTED_NON_CURRENT.value: "non_current",
    CandidateStatus.REJECTED_UNSAFE.value: "unsafe",
}


def parse_candidate_report(path: Path) -> list[ReportRow]:
    rows: list[ReportRow] = []
    section: Literal["accepted", "rejected"] | None = None
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Accepted":
            _append_current_row(rows, current, section)
            section = "accepted"
            current = None
            continue
        if line == "## Rejected":
            _append_current_row(rows, current, section)
            section = "rejected"
            current = None
            continue
        if line.startswith("- Source:"):
            _append_current_row(rows, current, section)
            current = {"source": line.split(":", 1)[1].strip()}
            continue
        if current is None or not line.startswith("- "):
            continue
        key, _, value = line[2:].partition(":")
        if not value:
            continue
        current[key.lower()] = value.strip()
    _append_current_row(rows, current, section)
    return rows


def build_review_worklist(rows: list[ReportRow]) -> list[ReviewWorklistItem]:
    return [_item_from_row(row) for row in rows]


def render_review_worklist_markdown(items: list[ReviewWorklistItem], *, candidate_report: Path) -> str:
    counts = Counter(item.state for item in items)
    lines = [
        "# Graphiti review worklist",
        "",
        f"Candidate report: {candidate_report}",
        "",
        "## Counts",
        "",
    ]
    if counts:
        lines.extend(f"- {state}: {count}" for state, count in sorted(counts.items()))
    else:
        lines.append("- none: 0")
    lines.extend(["", "## Items", ""])
    if not items:
        lines.append("No review worklist items.")
        return "\n".join(lines) + "\n"
    for item in items:
        lines.extend(
            [
                f"- Source: {item.source}",
                f"  - State: {item.state}",
                f"  - Classification: {item.classification}",
                f"  - Status: {item.status}",
                f"  - Detail: {item.detail}",
                f"  - Source exists: {str(item.source_exists).lower()}",
                f"  - Source fingerprint: {item.source_fingerprint}",
                "  - Excerpt: |",
            ]
        )
        excerpt = item.excerpt or ""
        lines.extend(f"      {excerpt_line}" for excerpt_line in excerpt.splitlines() or [""])
    return "\n".join(lines) + "\n"


def review_worklist_payload(items: list[ReviewWorklistItem], *, candidate_report: Path) -> dict:
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "candidate_report": str(candidate_report),
        "items": [_json_item(item) for item in items],
        "counts": dict(sorted(Counter(item.state for item in items).items())),
    }


def render_review_worklist_json(items: list[ReviewWorklistItem], *, candidate_report: Path) -> str:
    return json.dumps(review_worklist_payload(items, candidate_report=candidate_report), indent=2) + "\n"


def _append_current_row(
    rows: list[ReportRow],
    current: dict[str, str] | None,
    section: Literal["accepted", "rejected"] | None,
) -> None:
    if current is None or section is None:
        return
    source = current.get("source")
    status = current.get("status")
    if not source or not status:
        return
    rows.append(
        ReportRow(
            source=Path(source),
            section=cast(Literal["accepted", "rejected"], section),
            classification=current.get("classification", ""),
            status=status,
            detail=current.get("detail", ""),
        )
    )


def _item_from_row(row: ReportRow) -> ReviewWorklistItem:
    source_exists = row.source.is_file()
    state = "missing_source" if not source_exists else STATUS_TO_STATE.get(row.status, "needs_review")
    return ReviewWorklistItem(
        source=row.source,
        source_exists=source_exists,
        source_fingerprint=_source_fingerprint(row.source, source_exists=source_exists),
        state=state,
        classification=row.classification,
        status=row.status,
        detail=row.detail,
        excerpt=_source_excerpt(row.source) if source_exists else "",
    )


def _source_fingerprint(path: Path, *, source_exists: bool) -> str:
    resolved = str(path.expanduser().resolve(strict=False))
    digest = hashlib.sha256()
    digest.update(resolved.encode("utf-8"))
    if source_exists:
        digest.update(path.read_bytes())
    else:
        digest.update(b"missing")
    return digest.hexdigest()


def _source_excerpt(path: Path) -> str:
    excerpt_lines: list[str] = []
    size = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        remaining = EXCERPT_LIMIT - size
        if remaining <= 0:
            break
        excerpt_lines.append(stripped[:remaining])
        size += len(excerpt_lines[-1])
    return "\n".join(excerpt_lines)


def _json_item(item: ReviewWorklistItem) -> dict:
    payload = asdict(item)
    payload["source"] = str(item.source)
    return payload
