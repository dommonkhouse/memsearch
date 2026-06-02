from __future__ import annotations

from pathlib import Path

from ..models import BackfillManifestEntry, SourceFile


def classify_manus_source(path: str | Path) -> str:
    path_obj = Path(path)
    text = str(path_obj)
    if "indexeddb.leveldb" in text.lower() or "IndexedDB" in path_obj.parts:
        return "indexeddb_probe_only"
    if "Cache" in path_obj.parts or "Cache_Data" in path_obj.parts or "GPUCache" in path_obj.parts:
        return "cache_probe_only"
    return "unknown_format"


def probe_manus_source(source: SourceFile) -> BackfillManifestEntry:
    reason = classify_manus_source(source.path)
    return BackfillManifestEntry.from_source_file(source, status="skipped", last_error=reason)


def dedupe_manus_probe_entries(entries: list[BackfillManifestEntry]) -> list[BackfillManifestEntry]:
    seen: set[str] = set()
    deduped: list[BackfillManifestEntry] = []
    for entry in entries:
        if entry.conversation_key and entry.conversation_key in seen:
            deduped.append(
                BackfillManifestEntry(
                    product=entry.product,
                    machine=entry.machine,
                    source_path=entry.source_path,
                    file_size=entry.file_size,
                    mtime=entry.mtime,
                    content_hash=entry.content_hash,
                    status="duplicate_conversation",
                    generated_output_path=entry.generated_output_path,
                    last_error="duplicate_conversation",
                    conversation_key=entry.conversation_key,
                    transcript_fingerprint=entry.transcript_fingerprint,
                )
            )
            continue
        if entry.conversation_key:
            seen.add(entry.conversation_key)
        deduped.append(entry)
    return deduped
