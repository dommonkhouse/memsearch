from __future__ import annotations

import json
from pathlib import Path

from memsearch.backfill.inventory import collect_inventory
from memsearch.backfill.manifest import (
    apply_historical_dedupe,
    choose_preferred_sources,
    load_historical_source_index,
    read_manifest,
    write_manifest,
)
from memsearch.backfill.models import (
    BackfillManifestEntry,
    Conversation,
    SourceFile,
    Turn,
    machine_slug,
    normalise_machine_name,
)


def test_collect_inventory_labels_known_sources(tmp_path: Path) -> None:
    (tmp_path / ".claude/projects/foo").mkdir(parents=True)
    (tmp_path / ".claude/projects/foo/session.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / ".codex/sessions/2026/06/01").mkdir(parents=True)
    (tmp_path / ".codex/sessions/2026/06/01/rollout.jsonl").write_text("{}", encoding="utf-8")

    files = collect_inventory(home=tmp_path, machine="Test Mac")

    assert {f.product for f in files} == {"claude_code", "codex"}
    assert {f.machine for f in files} == {"Test Mac"}


def test_collect_inventory_marks_cache_and_export_precedence(tmp_path: Path) -> None:
    cache = tmp_path / "Library/Application Support/com.openai.chat/cache.json"
    export = tmp_path / "memsearch/.local/chat-exports/chatgpt/conversations.json"
    cache.parent.mkdir(parents=True)
    export.parent.mkdir(parents=True)
    cache.write_text("{}", encoding="utf-8")
    export.write_text("[]", encoding="utf-8")

    files = collect_inventory(home=tmp_path, repo_root=tmp_path / "memsearch", machine="Test Mac")

    by_product = {f.product: f for f in files}
    assert by_product["chatgpt_cache"].is_fallback
    assert not by_product["chatgpt_export"].is_fallback


def test_manifest_round_trip_includes_required_fields(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    source.write_text('{"type":"user"}\n', encoding="utf-8")
    source_file = SourceFile.from_path(source, product="codex", machine="Dominic's MacBook")
    entry = BackfillManifestEntry.from_source_file(
        source_file,
        conversation_key="codex:abc",
        status="converted",
        generated_output_path="/memory/imported.md",
    )

    manifest = tmp_path / "manifest-dominics-macbook.json"
    write_manifest(manifest, [entry])
    loaded = read_manifest(manifest)

    assert loaded == [entry]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert set(data["entries"][0]) >= {
        "product",
        "machine",
        "source_path",
        "file_size",
        "mtime",
        "content_hash",
        "status",
        "generated_output_path",
        "last_error",
        "conversation_key",
    }


def test_historical_manifest_and_markdown_anchors_mark_already_imported(tmp_path: Path) -> None:
    historical = tmp_path / "historical-sessions"
    historical.mkdir()
    source_from_manifest = tmp_path / ".claude/projects/foo/session.jsonl"
    source_from_anchor = tmp_path / ".codex/sessions/2026/05/07/rollout.jsonl"
    source_from_manifest.parent.mkdir(parents=True)
    source_from_anchor.parent.mkdir(parents=True)
    source_from_manifest.write_text("{}\n", encoding="utf-8")
    source_from_anchor.write_text("{}\n", encoding="utf-8")

    (historical / "manifest.json").write_text(
        json.dumps({"sessions": [{"source_jsonl": str(source_from_manifest), "session_id": "claude-1"}]}),
        encoding="utf-8",
    )
    (historical / "2026-05.md").write_text(
        "<!-- backfill-agent:codex session:codex-1 "
        f"transcript:{source_from_anchor} machine:Dominics-Mac-mini -->\n",
        encoding="utf-8",
    )

    sources = [
        SourceFile.from_path(source_from_manifest, product="claude_code", machine="Dominic's MacBook"),
        SourceFile.from_path(source_from_anchor, product="codex", machine="Dominic's Mac Mini"),
    ]
    index = load_historical_source_index(historical)
    entries = apply_historical_dedupe(sources, index)

    assert [entry.status for entry in entries] == ["already_imported", "already_imported"]
    assert entries[1].machine == "Dominic's Mac Mini"


def test_historical_anchor_recomputes_fingerprint_only_when_raw_source_exists(tmp_path: Path) -> None:
    historical = tmp_path / "historical-sessions"
    historical.mkdir()
    existing = tmp_path / ".codex/sessions/existing.jsonl"
    missing = tmp_path / ".codex/sessions/missing.jsonl"
    existing.parent.mkdir(parents=True)
    existing.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "message": "Hello /Users/alice/project"}),
                json.dumps({"type": "assistant", "message": "World 123e4567-e89b-12d3-a456-426614174000"}),
            ]
        ),
        encoding="utf-8",
    )
    (historical / "anchors.md").write_text(
        "\n".join(
            [
                f"<!-- backfill-agent:codex session:existing transcript:{existing} machine:Dominics-Macbook -->",
                f"<!-- backfill-agent:codex session:missing transcript:{missing} machine:Dominics-Macbook -->",
            ]
        ),
        encoding="utf-8",
    )

    index = load_historical_source_index(historical)

    assert index.by_transcript_path[str(existing)].fingerprint is not None
    assert index.by_transcript_path[str(missing)].fingerprint is None


def test_preferred_sources_use_exports_before_cache_and_dedupe_by_conversation_key() -> None:
    cache = SourceFile(path=Path("/cache/chatgpt"), product="chatgpt_cache", machine="MacBook", is_fallback=True)
    export = SourceFile(path=Path("/export/chatgpt"), product="chatgpt_export", machine="MacBook", is_fallback=False)
    claude_cache = SourceFile(path=Path("/cache/claude"), product="claude_cache", machine="MacBook", is_fallback=True)
    claude_export = SourceFile(path=Path("/export/claude"), product="claude_export", machine="MacBook", is_fallback=False)

    conversations = [
        Conversation(source=cache, product="chatgpt_cache", machine="MacBook", platform_id="gpt-1", turns=[]),
        Conversation(source=export, product="chatgpt_export", machine="MacBook", platform_id="gpt-1", turns=[]),
        Conversation(source=claude_cache, product="claude_cache", machine="MacBook", platform_id="claude-1", turns=[]),
        Conversation(source=claude_export, product="claude_export", machine="MacBook", platform_id="claude-1", turns=[]),
        Conversation(
            source=SourceFile(path=Path("/mini/manus"), product="manus_cache", machine="Mini", is_fallback=True),
            product="manus_cache",
            machine="Mini",
            platform_id="manus-1",
            turns=[],
        ),
        Conversation(
            source=SourceFile(path=Path("/book/manus"), product="manus_cache", machine="MacBook", is_fallback=True),
            product="manus_cache",
            machine="MacBook",
            platform_id="manus-1",
            turns=[],
        ),
    ]

    preferred = choose_preferred_sources(conversations)

    assert [c.product for c in preferred] == ["chatgpt_export", "claude_export", "manus_cache"]
    assert preferred[2].machine == "Mini"


def test_claude_desktop_code_sessions_default_to_possible_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "Library/Application Support/Claude/claude-code-sessions/session.json"
    source.parent.mkdir(parents=True)
    source.write_text("{}", encoding="utf-8")

    files = collect_inventory(home=tmp_path, machine="Test Mac")

    assert files[0].product == "claude_desktop_code_session"
    assert files[0].status == "possible_duplicate_claude_code"


def test_machine_slug_normalisation_matches_old_historical_names() -> None:
    assert normalise_machine_name("Dominics-Mac-mini") == "Dominic's Mac Mini"
    assert normalise_machine_name("Dominics-Macbook") == "Dominic's MacBook"
    assert machine_slug("Dominic's Mac Mini") == "dominics-mac-mini"


def test_fingerprint_normalises_paths_uuids_and_whitespace() -> None:
    source_a = SourceFile(path=Path("/a.jsonl"), product="codex", machine="A")
    source_b = SourceFile(path=Path("/b.jsonl"), product="codex", machine="B")
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    conversation_a = Conversation(
        source=source_a,
        product="codex",
        machine="A",
        turns=[
            Turn(role="User", text="Keep /Users/dominicmonkhouse/Projects/foo"),
            Turn(role="assistant", text=f"Done {uuid}"),
        ],
    )
    conversation_b = Conversation(
        source=source_b,
        product="codex",
        machine="B",
        turns=[
            Turn(role="user", text=" Keep /Users/someone/Projects/foo "),
            Turn(role="Assistant", text="Done"),
        ],
    )

    assert conversation_a.normalised_fingerprint_text() == conversation_b.normalised_fingerprint_text()
    assert conversation_a.transcript_fingerprint() == conversation_b.transcript_fingerprint()
