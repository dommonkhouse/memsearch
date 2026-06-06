from __future__ import annotations

import json
import re
from pathlib import Path

from .models import (
    BackfillManifestEntry,
    Conversation,
    HistoricalSourceAnchor,
    HistoricalSourceIndex,
    SourceFile,
    loose_jsonl_conversation,
    normalise_machine_name,
)

ANCHOR_RE = re.compile(r"<!--\s*backfill-agent:(?P<product>\S+)(?P<body>.*?)-->", re.DOTALL)
FIELD_RE = re.compile(r"(?P<key>session|transcript|machine):(?P<value>.*?)(?=\s+\w+:|$)")


def write_manifest(path: Path, entries: list[BackfillManifestEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "entries": [entry.to_json() for entry in sorted(entries, key=lambda e: (e.machine, e.source_path))],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_manifest(path: Path) -> list[BackfillManifestEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload if isinstance(payload, list) else [])
    return [BackfillManifestEntry.from_json(entry) for entry in entries]


def manifest_path(base_dir: Path, machine_slug: str) -> Path:
    return base_dir / f"manifest-{machine_slug}.json"


def load_all_manifests(base_dir: Path) -> list[BackfillManifestEntry]:
    entries: list[BackfillManifestEntry] = []
    for path in sorted(base_dir.glob("manifest-*.json")):
        entries.extend(read_manifest(path))
    return entries


def load_historical_source_index(historical_dir: Path) -> HistoricalSourceIndex:
    by_source_path: dict[str, HistoricalSourceAnchor] = {}
    by_transcript_path: dict[str, HistoricalSourceAnchor] = {}
    by_session_id: dict[str, HistoricalSourceAnchor] = {}
    by_fingerprint: dict[str, HistoricalSourceAnchor] = {}

    manifest = historical_dir / "manifest.json"
    if manifest.is_file():
        _load_historical_manifest(manifest, by_source_path, by_transcript_path, by_session_id)

    for markdown in sorted(historical_dir.rglob("*.md")):
        for anchor in _anchors_from_markdown(markdown):
            _store_anchor(anchor, by_source_path, by_transcript_path, by_session_id, by_fingerprint)

    return HistoricalSourceIndex(
        by_source_path=by_source_path,
        by_transcript_path=by_transcript_path,
        by_session_id=by_session_id,
        by_fingerprint=by_fingerprint,
    )


def apply_historical_dedupe(sources: list[SourceFile], index: HistoricalSourceIndex) -> list[BackfillManifestEntry]:
    entries: list[BackfillManifestEntry] = []
    for source in sources:
        anchor = index.by_source_path.get(str(source.path)) or index.by_transcript_path.get(str(source.path))
        if anchor:
            entries.append(
                BackfillManifestEntry.from_source_file(
                    source,
                    conversation_key=anchor.session_id,
                    status="already_imported",
                    transcript_fingerprint=anchor.fingerprint or "",
                )
            )
        else:
            entries.append(source.to_manifest_entry())
    return entries


def choose_preferred_sources(conversations: list[Conversation]) -> list[Conversation]:
    chosen: dict[str, Conversation] = {}
    order: list[str] = []
    for conversation in conversations:
        key = conversation.conversation_key
        if key not in chosen:
            chosen[key] = conversation
            order.append(key)
            continue
        if _source_rank(conversation) > _source_rank(chosen[key]):
            chosen[key] = conversation
    return [chosen[key] for key in order]


def _source_rank(conversation: Conversation) -> tuple[int, int]:
    product = conversation.product
    official = 1 if product.endswith("_export") else 0
    primary = 0 if conversation.source.is_fallback else 1
    return official, primary


def _load_historical_manifest(
    manifest: Path,
    by_source_path: dict[str, HistoricalSourceAnchor],
    by_transcript_path: dict[str, HistoricalSourceAnchor],
    by_session_id: dict[str, HistoricalSourceAnchor],
) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    raw_entries = payload.get("sessions") or payload.get("entries") or []
    for raw in raw_entries:
        source_path = str(raw.get("source_jsonl") or raw.get("source_path") or raw.get("transcript") or "")
        if not source_path:
            continue
        session_id = str(raw.get("session_id") or raw.get("conversation_key") or source_path)
        product = str(raw.get("product") or "")
        machine = normalise_machine_name(str(raw.get("machine") or ""))
        anchor = HistoricalSourceAnchor(product=product, session_id=session_id, transcript_path=source_path, machine=machine)
        by_source_path[source_path] = anchor
        by_transcript_path[source_path] = anchor
        by_session_id[session_id] = anchor


def _anchors_from_markdown(path: Path) -> list[HistoricalSourceAnchor]:
    text = path.read_text(encoding="utf-8")
    anchors: list[HistoricalSourceAnchor] = []
    for match in ANCHOR_RE.finditer(text):
        product = match.group("product")
        fields = {field.group("key"): field.group("value").strip() for field in FIELD_RE.finditer(match.group("body"))}
        transcript_path = fields.get("transcript", "")
        session_id = fields.get("session", transcript_path)
        machine = normalise_machine_name(fields.get("machine", ""))
        fingerprint = _fingerprint_if_raw_exists(transcript_path, product=product, machine=machine)
        anchors.append(
            HistoricalSourceAnchor(
                product=product,
                session_id=session_id,
                transcript_path=transcript_path,
                machine=machine,
                fingerprint=fingerprint,
            )
        )
    return anchors


def _store_anchor(
    anchor: HistoricalSourceAnchor,
    by_source_path: dict[str, HistoricalSourceAnchor],
    by_transcript_path: dict[str, HistoricalSourceAnchor],
    by_session_id: dict[str, HistoricalSourceAnchor],
    by_fingerprint: dict[str, HistoricalSourceAnchor],
) -> None:
    if anchor.transcript_path:
        by_source_path[anchor.transcript_path] = anchor
        by_transcript_path[anchor.transcript_path] = anchor
    if anchor.session_id:
        by_session_id[anchor.session_id] = anchor
    if anchor.fingerprint:
        by_fingerprint[anchor.fingerprint] = anchor


def _fingerprint_if_raw_exists(transcript_path: str, *, product: str, machine: str) -> str | None:
    if not transcript_path:
        return None
    path = Path(transcript_path)
    if not path.is_file():
        return None
    conversation = loose_jsonl_conversation(path, product=product, machine=machine)
    text = conversation.normalised_fingerprint_text()
    return conversation.transcript_fingerprint() if text else None
