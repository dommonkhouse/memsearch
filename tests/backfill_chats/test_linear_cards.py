from __future__ import annotations

import json
from pathlib import Path

from memsearch.backfill.linear_api import LinearIssue
from memsearch.backfill.linear_cards import render_linear_issue_card, write_linear_cards, write_linear_export
from memsearch.backfill.redact import scan_path_for_secrets


def test_linear_card_contains_issue_anchor_and_redacts_secrets() -> None:
    issue = LinearIssue(
        id="id",
        identifier="MON-318",
        title="Use OPENAI_API_KEY=abc123456789",
        url="https://linear.app/issue/MON-318",
        description="Comment says Authorization: Bearer secretbearertoken123",
        updated_at="2026-06-11T00:00:00Z",
        state="Todo",
        team="MON",
        comments=({"body": "No secret", "user": "Dominic", "created_at": "2026-06-11T00:00:00Z"},),
    )

    card = render_linear_issue_card(issue, machine="Test Mac")

    assert "backfill-agent:linear issue:MON-318 source:linear machine:test-mac" in card
    assert "secretbearertoken123" not in card
    assert "OPENAI_API_KEY=[REDACTED]" in card


def test_linear_export_and_cards_write_deterministic_markdown(tmp_path: Path) -> None:
    issue = LinearIssue(
        id="id",
        identifier="MON-318",
        title="Freshness plan",
        url="https://linear.app/issue/MON-318",
        updated_at="2026-06-11T00:00:00Z",
        state="Todo",
        team="MON",
    )
    run_dir = tmp_path / "run"
    output = tmp_path / "cards"

    export_summary = write_linear_export(run_dir, issues=[issue], machine="Test Mac", since="2026-06-10T00:00:00Z", run_id="run-1")
    card_summary = write_linear_cards(run_dir, output, machine="Test Mac")
    manifest = json.loads((output / "card-manifest.json").read_text(encoding="utf-8"))
    markdown = (output / "memory" / "linear" / "test-mac" / "2026-06.md").read_text(encoding="utf-8")

    assert export_summary["issue_count"] == 1
    assert card_summary["issue_cards"] == 1
    assert manifest["issue_ids"] == ["MON-318"]
    assert "Linear issue MON-318" in markdown
    assert scan_path_for_secrets(output) == []
