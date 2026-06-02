from __future__ import annotations

from pathlib import Path

from memsearch.backfill.models import BackfillManifestEntry, SourceFile
from memsearch.backfill.parsers.manus import classify_manus_source, dedupe_manus_probe_entries, probe_manus_source


def test_probe_manus_classifies_indexeddb_cache_and_unknown(tmp_path: Path) -> None:
    indexeddb = tmp_path / "Library/Application Support/Manus/IndexedDB/app_manus_0.indexeddb.leveldb/000001.ldb"
    cache = tmp_path / "Library/Application Support/Manus/Cache/Cache_Data/cache_0"
    unknown = tmp_path / "Library/Application Support/Manus/Preferences"
    for path in [indexeddb, cache, unknown]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"data")

    assert classify_manus_source(indexeddb) == "indexeddb_probe_only"
    assert classify_manus_source(cache) == "cache_probe_only"
    assert classify_manus_source(unknown) == "unknown_format"


def test_probe_manus_returns_skipped_manifest_entry(tmp_path: Path) -> None:
    path = tmp_path / "Library/Application Support/Google/Chrome/Default/IndexedDB/https_manus.im_0.indexeddb.leveldb/000001.ldb"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")
    source = SourceFile.from_path(path, product="manus_indexeddb", machine="Test Mac", source_kind="indexeddb", is_fallback=True)

    entry = probe_manus_source(source)

    assert entry.status == "skipped"
    assert entry.last_error == "indexeddb_probe_only"
    assert entry.product == "manus_indexeddb"


def test_dedupe_manus_probe_entries_marks_duplicate_conversation_keys() -> None:
    first = BackfillManifestEntry(
        product="manus_indexeddb",
        machine="MacBook",
        source_path="/book",
        file_size=1,
        mtime=1,
        content_hash="sha256:a",
        status="converted",
        conversation_key="platform:manus-1",
    )
    second = BackfillManifestEntry(
        product="manus_indexeddb",
        machine="Mini",
        source_path="/mini",
        file_size=1,
        mtime=1,
        content_hash="sha256:b",
        status="converted",
        conversation_key="platform:manus-1",
    )

    deduped = dedupe_manus_probe_entries([first, second])

    assert deduped[0].status == "converted"
    assert deduped[1].status == "duplicate_conversation"
    assert deduped[1].last_error == "duplicate_conversation"
