from __future__ import annotations

from pathlib import Path

from memsearch.graphiti.backup import backup_path_for_timestamp


def test_backup_path_stays_under_graphiti_ssd_root():
    path = backup_path_for_timestamp(Path("/Volumes/SSD/graphiti-mon316/backups"), "20260614-120000")

    assert path == Path("/Volumes/SSD/graphiti-mon316/backups/20260614-120000")


def test_backup_path_rejects_traversal():
    try:
        backup_path_for_timestamp(Path("/Volumes/SSD/graphiti-mon316/backups"), "../bad")
    except ValueError as exc:
        assert "invalid backup timestamp" in str(exc)
    else:
        raise AssertionError("expected invalid timestamp rejection")
