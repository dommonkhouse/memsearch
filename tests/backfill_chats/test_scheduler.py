from __future__ import annotations

import plistlib
from pathlib import Path

from memsearch.backfill.scheduler import render_scheduler_plists


def test_scheduler_render_writes_daily_and_weekly_plists_without_installing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    summary = render_scheduler_plists(output=tmp_path / "launchagents", repo_root=repo, machine="Test Mac")
    daily = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.daily-linear-sync.plist").read_bytes())
    weekly = plistlib.loads((tmp_path / "launchagents" / "com.memsearch.weekly-manus-sync.plist").read_bytes())

    assert summary["installed"] is False
    assert daily["StartCalendarInterval"] == {"Hour": 6, "Minute": 30}
    assert weekly["StartCalendarInterval"] == {"Weekday": 1, "Hour": 6, "Minute": 0}
    assert daily["ProgramArguments"][0] == "/bin/zsh"
    assert Path(daily["ProgramArguments"][0]).is_absolute()
    assert "source" in daily["ProgramArguments"][2]
    assert "--index" in daily["ProgramArguments"][2]
    assert "--index" in weekly["ProgramArguments"][2]
    assert ".secrets/mcp.env" in daily["ProgramArguments"][2]
    assert daily["WorkingDirectory"] == str(repo)
    assert str(repo / ".local" / "source-sync-logs") in daily["StandardOutPath"]
