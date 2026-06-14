from __future__ import annotations

import plistlib

from memsearch.backfill.scheduler import render_scheduler_plists


def test_scheduler_renders_graphiti_watchdog(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-watchdog" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.monkhouse.graphiti-mon316-watchdog.plist").read_bytes())
    assert payload["Label"] == "com.monkhouse.graphiti-mon316-watchdog"
    assert payload["StartInterval"] == 300
    assert payload["RunAtLoad"] is True
    assert "graphiti-watchdog-mon316.sh" in " ".join(payload["ProgramArguments"])


def test_scheduler_renders_graphiti_backup(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-backup" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.monkhouse.graphiti-mon316-backup.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Hour": 3, "Minute": 15}
    assert "graphiti-backup-mon316.sh" in " ".join(payload["ProgramArguments"])


def test_scheduler_renders_source_freshness_proof(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.memsearch.source-freshness-proof" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.source-freshness-proof.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Hour": 6, "Minute": 45}
    assert "graphiti-source-freshness-proof-mon316.sh" in " ".join(payload["ProgramArguments"])


def test_scheduler_renders_graphiti_candidate_report(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's Mac mini")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.memsearch.graphiti-candidate-report" in labels

    payload = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.graphiti-candidate-report.plist").read_bytes())
    assert payload["StartCalendarInterval"] == {"Weekday": 1, "Hour": 7, "Minute": 0}
    assert "graphiti-candidate-report-mon316.sh" in " ".join(payload["ProgramArguments"])


def test_scheduler_does_not_render_graphiti_mini_jobs_on_macbook(tmp_path):
    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=tmp_path, machine="Dominic's MacBook Pro")

    labels = {item["label"] for item in summary["plists"]}
    assert "com.monkhouse.graphiti-mon316-watchdog" not in labels
    assert "com.monkhouse.graphiti-mon316-backup" not in labels
    assert "com.memsearch.source-freshness-proof" not in labels
    assert "com.memsearch.graphiti-candidate-report" not in labels
