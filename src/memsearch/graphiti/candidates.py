"""Deterministic candidate filtering for reviewed Graphiti seed reports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CandidateStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED_RAW_SOURCE = "rejected_raw_source"
    REJECTED_STALE_ROUTE = "rejected_stale_route"
    REJECTED_MISSING_CLASSIFICATION = "rejected_missing_classification"
    REJECTED_MISSING_EVIDENCE = "rejected_missing_evidence"
    REJECTED_NON_CURRENT = "rejected_non_current"
    REJECTED_UNSAFE = "rejected_unsafe"


@dataclass(frozen=True)
class CandidateItem:
    source: Path
    status: CandidateStatus
    classification: str
    detail: str


@dataclass(frozen=True)
class CandidateReport:
    accepted: list[CandidateItem]
    rejected: list[CandidateItem]


VALID_CLASSIFICATIONS = {"current", "historical", "superseded", "unsafe"}
STALE_ROUTE_TOKENS = (".nord", "Meshnet", "100.87.225.99", "restart NordVPN", "restart Meshnet")
RAW_SOURCE_PARTS = {".memsearch", "raw", "raw-chats", "transcripts", "transcript-dumps", "manus-api-export"}


def build_candidate_report(paths: Iterable[Path]) -> CandidateReport:
    accepted: list[CandidateItem] = []
    rejected: list[CandidateItem] = []
    for path in _expand_candidate_paths(paths):
        body = path.read_text(encoding="utf-8", errors="replace")
        classification = _classification(body)
        stale_status = _stale_status(body, classification)
        if _is_raw_source(path):
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_RAW_SOURCE, classification, "raw source path"))
        elif not classification:
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_MISSING_CLASSIFICATION, "", "missing Classification marker"))
        elif classification not in VALID_CLASSIFICATIONS:
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_MISSING_CLASSIFICATION, classification, "unknown classification"))
        elif "Evidence:" not in body:
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_MISSING_EVIDENCE, classification, "missing Evidence marker"))
        elif stale_status is not None:
            rejected.append(CandidateItem(path, stale_status, classification, "stale route token"))
        elif classification == "unsafe":
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_UNSAFE, classification, "unsafe classification"))
        elif classification != "current":
            rejected.append(CandidateItem(path, CandidateStatus.REJECTED_NON_CURRENT, classification, "not current"))
        else:
            accepted.append(CandidateItem(path, CandidateStatus.ACCEPTED, classification, "eligible for human review"))
    return CandidateReport(accepted=accepted, rejected=rejected)


def render_candidate_report(report: CandidateReport) -> str:
    lines = ["# Graphiti candidate report", "", "## Accepted", ""]
    if report.accepted:
        for item in report.accepted:
            lines.extend(
                [
                    f"- Source: {item.source}",
                    f"  - Classification: {item.classification}",
                    f"  - Status: {item.status.value}",
                ]
            )
    else:
        lines.append("No accepted candidates.")
    lines.extend(["", "## Rejected", ""])
    if report.rejected:
        for item in report.rejected:
            lines.extend(
                [
                    f"- Source: {item.source}",
                    f"  - Classification: {item.classification or 'missing'}",
                    f"  - Status: {item.status.value}",
                    f"  - Detail: {item.detail}",
                ]
            )
    else:
        lines.append("No rejected candidates.")
    return "\n".join(lines) + "\n"


def _expand_candidate_paths(paths: Iterable[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        candidate = Path(path)
        if candidate.is_dir():
            expanded.extend(sorted(candidate.rglob("*.md")))
        elif candidate.is_file():
            expanded.append(candidate)
    return expanded


def _classification(body: str) -> str:
    for line in body.splitlines():
        if line.lower().startswith("classification:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def _is_raw_source(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if "linear" in parts and "memory" in parts:
        return False
    if {"antigravity", "gemini_cli", "memory"} <= parts:
        return False
    return bool(parts & RAW_SOURCE_PARTS and "graphiti-curated-seeds" not in "/".join(parts))


def _stale_status(body: str, classification: str) -> CandidateStatus | None:
    if classification in {"historical", "superseded"}:
        return None
    if any(token.lower() in body.lower() for token in STALE_ROUTE_TOKENS):
        return CandidateStatus.REJECTED_STALE_ROUTE
    return None
