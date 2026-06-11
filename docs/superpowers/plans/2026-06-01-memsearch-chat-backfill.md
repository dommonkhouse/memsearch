# Memsearch Chat Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified backfill pipeline that imports missing Claude Code, Codex, Claude Desktop/Cowork, Claude Chat, ChatGPT, and Manus conversations into Memsearch as canonical markdown memory.

**Architecture:** Add a source-normalisation pipeline that reads local transcript/export files, converts them into canonical markdown grouped by machine/source/month, writes a manifest for repeatable incremental runs, and then indexes those markdown files with the existing `memsearch index` CLI. Keep Milvus as a rebuildable derived index; the generated markdown and manifests are the source of truth.

**Tech Stack:** Python 3.10+, stdlib JSON/HTML parsing, pytest, existing `uv run python -m pytest` test gate, existing `memsearch index/search/expand/stats`, SSH to Mac Mini for read-only source inventory.

**Linear:** `MON-321` - https://linear.app/monkhouseandcompany/issue/MON-321/memsearch-chat-backfill-implementation-plan

---

## Current State

- Existing Memsearch historical backfill files are present under `/Users/dominicmonkhouse/Projects/.memsearch/memory/historical-sessions/`.
- Existing backfill coverage found:
  - MacBook Claude Code: 716 sessions in generated markdown.
  - MacBook Codex: 110 sessions in generated markdown.
  - Mac Mini Claude Code: 585 sessions in generated markdown.
  - Mac Mini Codex: 25 sessions in generated markdown.
- Current source inventories are larger than the existing backfill:
  - MacBook: 1,772 Claude Code JSONL files and 228 Codex rollout JSONL files.
  - Mac Mini: 814 Claude Code JSONL files and 68 Codex rollout JSONL files.
- Claude Desktop/Cowork local-agent stores exist and must be treated separately from normal Claude Code:
  - MacBook: 403 local-agent JSONL files, 1,708 local-agent JSON files, 519 Claude Desktop code-session JSON files.
  - Mac Mini: 4 local-agent JSONL files, 9 local-agent JSON files, 488 Claude Desktop code-session JSON files.
- ChatGPT and Claude Chat official exports have not yet been downloaded on either machine.
- ChatGPT desktop cache exists but is a fallback source, not the source of truth.
- Manus app and Chrome IndexedDB stores exist on both machines, but the export route is still unknown.

## Files and Responsibilities

- Create: `src/memsearch/backfill/__init__.py`
  - Marks the backfill pipeline package.
- Create: `src/memsearch/backfill/__main__.py`
  - Allows `uv run python -m memsearch.backfill ...` as a short CLI entry point.
- Create: `src/memsearch/backfill/models.py`
  - Dataclasses for `SourceFile`, `Conversation`, `Turn`, `BackfillManifestEntry`, `HistoricalSourceIndex`, and `BackfillRunSummary`.
  - Each `Conversation` exposes a stable `conversation_key`: prefer platform conversation/session id, otherwise `(product, machine, source_path)`, otherwise a normalised transcript fingerprint.
  - The normalised transcript fingerprint is `sha256` over the first 20 chronological user/assistant turns after trimming whitespace, collapsing internal whitespace, lowercasing role names, removing volatile source paths and UUID-like ids, and excluding timestamps/tool output. UUID-like ids are removed with the exact case-insensitive regex `\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b`; volatile absolute paths are normalised by replacing `/Users/<name>/...` path tokens with `[PATH]`. Fixture tests must prove that the same conversation from two machines produces byte-identical normalised text before hashing and then the same fingerprint.
- Create: `src/memsearch/backfill/inventory.py`
  - Finds local source files for Claude Code, Codex, Claude Desktop/Cowork, ChatGPT cache, Claude cache, Manus cache, and downloaded exports.
  - Supports local MacBook inventory and Mac Mini inventory via a supplied root/snapshot path, not direct write access.
  - Classifies cache sources as fallback candidates. Official exports win over desktop/IndexedDB cache when both contain the same conversation id or transcript fingerprint.
- Create: `src/memsearch/backfill/parsers/claude_code.py`
  - Parses full Claude Code JSONL transcripts under `~/.claude/projects`.
  - Reuses the same tool-output exclusion rules as `plugins/claude-code/hooks/parse-transcript.sh`, but parses full sessions, not just the last turn.
- Create: `src/memsearch/backfill/parsers/codex.py`
  - Parses full Codex rollout JSONL files under `~/.codex/sessions`.
  - Reuses the same tool-output exclusion rules as `plugins/codex/scripts/parse-rollout.sh`, but parses full sessions, not just the last turn.
- Create: `src/memsearch/backfill/parsers/claude_desktop.py`
  - Parses Claude Desktop/Cowork local-agent JSONL and session JSON after format sampling proves which files contain actual conversation turns.
  - Excludes audit logs, subagent transcripts by default, plugin bundles, generated dependency folders, and tool dumps.
  - Treats `claude-code-sessions` as duplicate candidates by default. A Claude Desktop/Cowork record is "Cowork-only" only when sampled metadata or path proves it came from `local-agent-mode-sessions`, it contains user/assistant turns, and it has no matching Claude Code source path, session id, or transcript fingerprint in `~/.claude/projects` or existing historical anchors. Unknown shapes stay skipped as `unknown_format`.
- Create: `src/memsearch/backfill/parsers/chatgpt_export.py`
  - Parses official ChatGPT export artefacts, prioritising `conversations.json` if present and falling back to `chat.html` only when needed.
- Create: `src/memsearch/backfill/parsers/claude_export.py`
  - Parses official Claude data export conversations.
- Create: `src/memsearch/backfill/parsers/manus.py`
  - Initially exposes inventory and format probes only.
  - Adds conversation parsing only after the official export/API/cache route is confirmed.
- Create: `src/memsearch/backfill/render.py`
  - Renders canonical markdown sections with source anchors, machine, product, account/export identifier, title, time range, source path or export hash, and clean turns/summary.
  - Writes generated markdown under a machine slug directory, for example `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-macbook/<product>/<yyyy-mm>.md` and `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-mac-mini/<product>/<yyyy-mm>.md`, so Mini `rsync` cannot overwrite MacBook markdown.
- Create: `src/memsearch/backfill/redact.py`
  - Redacts obvious secrets before markdown write: API keys, bearer tokens, application passwords, OAuth tokens, cookie headers, and `.env`-style secrets.
- Create: `src/memsearch/backfill/manifest.py`
  - Reads and writes deterministic per-machine JSON manifests so backfills are incremental and idempotent.
  - Stores manifests under `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/` as `manifest-<machine-slug>.json`, for example `manifest-dominics-macbook.json` and `manifest-dominics-mac-mini.json`.
  - Commands that need full state load all `manifest-*.json` files and union entries by `(machine, source_path)` and `conversation_key`.
  - Reads `/Users/dominicmonkhouse/Projects/.memsearch/memory/historical-sessions/manifest.json` and marks previously converted source paths as `already_imported`.
  - Also scans existing historical markdown anchors under `/Users/dominicmonkhouse/Projects/.memsearch/memory/historical-sessions/**/*.md`, because the surviving old `manifest.json` can represent only the last machine run. The old markdown anchors are required to detect already-imported Mac Mini sessions.
  - Historical markdown anchors provide only product, session id, transcript path, and machine slug. They are matched by platform/session id and transcript path first. If the original transcript path still exists, the importer may recompute the normalised transcript fingerprint from the raw source; if the raw transcript is unavailable, old-anchor dedupe does not pretend a fingerprint exists.
- Create: `src/memsearch/backfill/cli.py`
  - CLI entry point for inventory, pilot conversion, full conversion, and verification search probes.
- Create: `tests/backfill_chats/__init__.py`
  - Matches the existing `tests/` package convention.
- Create: `tests/backfill_chats/test_inventory.py`
  - Tests source discovery and machine/source labelling.
- Create: `tests/backfill_chats/test_parse_claude_code.py`
  - Tests full-session Claude Code parsing and tool-output stripping.
- Create: `tests/backfill_chats/test_parse_codex.py`
  - Tests full-session Codex parsing and tool-output stripping.
- Create: `tests/backfill_chats/test_parse_claude_desktop.py`
  - Tests Claude Desktop/Cowork JSONL and JSON sample parsing once sample shapes are captured.
- Create: `tests/backfill_chats/test_parse_chatgpt_export.py`
  - Tests official ChatGPT export parsing.
- Create: `tests/backfill_chats/test_parse_claude_export.py`
  - Tests official Claude export parsing.
- Create: `tests/backfill_chats/test_redact.py`
  - Tests secret redaction.
- Create: `tests/backfill_chats/test_render.py`
  - Tests markdown anchors, headings, deterministic grouping, and source metadata.
- Create: `docs/backfill-chat-sources.md`
  - Operator documentation for requesting exports, placing export zips, running pilot/full backfills, and verifying recall.
- Modify: `.gitignore`
  - Add `.local/` in Task 1 so downloaded chat export archives cannot be committed accidentally before later export tasks run.

## Not Included In This Version

- No production/live WordPress work. This plan does not touch WordPress.
- No deletion, archive, or cleanup of existing transcript/cache files. Source files remain read-only.
- No direct Milvus destructive operations such as `memsearch reset`.
- No ChatGPT product-history pull via OpenAI API. OpenAI's documented route for ChatGPT product history is data export; local cache is fallback only.
- No manual user copy-paste steps unless a platform has no export/API/cache route. Agents should use available local files, browser automation, or official exported archives first.
- No broad Manus ingestion until the route is proven. Manus starts with inventory and sample parsing because the export surface is unclear.
- No indexing of raw exports or raw tool output. Only normalised, redacted markdown is indexed.

## Open Decisions

- Where downloaded official export zips should live. Resolved local path: `/Users/dominicmonkhouse/Projects/memsearch/.local/chat-exports/`, ignored by git via this plan.
- Whether subagent transcripts inside Claude Desktop/Cowork local-agent sessions should be indexed. Proposed default: exclude unless a parent session references them as user-visible work.
- Whether generated markdown should live in the repo or the existing memory store. Resolved output: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/` so markdown feeds the current collection without committing private transcripts.
- Whether Mac Mini conversion should run on the Mini and copy markdown back, or whether source snapshots should be pulled read-only to the MacBook. Resolved default: run inventory/conversion on the machine that owns the source paths, then copy Mini-generated markdown back to the MacBook with `rsync` before indexing from the MacBook.

## Task 1: Source Inventory Manifest

**Files:**
- Create: `src/memsearch/backfill/__init__.py`
- Create: `src/memsearch/backfill/__main__.py`
- Create: `src/memsearch/backfill/models.py`
- Create: `src/memsearch/backfill/inventory.py`
- Create: `src/memsearch/backfill/manifest.py`
- Create: `src/memsearch/backfill/cli.py`
- Create: `tests/backfill_chats/__init__.py`
- Test: `tests/backfill_chats/test_inventory.py`

- [ ] **Step 1: Write the failing inventory tests**

```python
from pathlib import Path

from memsearch.backfill.inventory import collect_inventory


def test_collect_inventory_labels_known_sources(tmp_path: Path):
    (tmp_path / ".claude/projects/foo").mkdir(parents=True)
    (tmp_path / ".claude/projects/foo/session.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / ".codex/sessions/2026/06/01").mkdir(parents=True)
    (tmp_path / ".codex/sessions/2026/06/01/rollout.jsonl").write_text("{}", encoding="utf-8")

    files = collect_inventory(home=tmp_path, machine="Test Mac")

    assert {f.product for f in files} == {"claude_code", "codex"}
    assert {f.machine for f in files} == {"Test Mac"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/backfill_chats/test_inventory.py -v`

Expected: FAIL because `memsearch.backfill.inventory` does not exist.

- [ ] **Step 3: Implement minimal models and inventory**

Create dataclasses for source files and implement read-only discovery for:
- `~/.claude/projects/**/*.jsonl`
- `~/.codex/sessions/**/*.jsonl`
- `~/Library/Application Support/Claude/local-agent-mode-sessions/**/*.jsonl`
- `~/Library/Application Support/Claude/local-agent-mode-sessions/**/*.json`
- `~/Library/Application Support/Claude/claude-code-sessions/**/*.json`
- `~/Library/Application Support/com.openai.chat/**/*`
- `~/Library/Application Support/Manus/**/*`
- `~/Library/Application Support/Google/Chrome/Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb/**/*`
- `~/Library/Application Support/Google/Chrome/Default/IndexedDB/https_claude.ai_0.indexeddb.leveldb/**/*`
- `~/Library/Application Support/Google/Chrome/Default/IndexedDB/https_manus.im_0.indexeddb.leveldb/**/*`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/backfill_chats/test_inventory.py -v`

Expected: PASS.

- [ ] **Step 5: Add manifest write/read and existing-backfill dedup tests**

Test that manifest entries include product, machine, source path, file size, mtime, content hash, status, generated output path, and last error. Add a fixture matching the existing `historical-sessions/manifest.json` shape and verify those `source_jsonl` paths are marked `already_imported` rather than converted again.

Add a second fixture matching existing historical markdown anchors:

```markdown
<!-- backfill-agent:codex session:2026-05-07T14-37-36-... transcript:/Users/dominicmonkhouse/.codex/sessions/2026/05/07/rollout-2026-05-07T14-37-36-....jsonl machine:Dominics-Mac-mini -->
```

Verify those transcript paths are also marked `already_imported`, even when they are absent from `historical-sessions/manifest.json`.

Add a fixture where an old historical anchor has a transcript path that still exists locally. Expected: the old anchor marks the source as `already_imported` by transcript path, and the raw transcript can also be parsed to compute the same normalised fingerprint as a new duplicate candidate. Add a second fixture where the raw transcript path is missing. Expected: the old anchor still dedupes by session id/transcript path, but no fingerprint is fabricated.

Add cross-source dedupe tests:
- official ChatGPT export beats ChatGPT desktop cache for the same conversation id
- official Claude export beats Claude IndexedDB cache for the same conversation id
- Manus cache entries from MacBook and Mac Mini collapse to one conversation when their platform id or transcript fingerprint matches
- Claude Desktop `claude-code-sessions` entries are skipped as `possible_duplicate_claude_code` unless sample parsing proves they contain Cowork-only conversation content not present in `~/.claude/projects`; Cowork-only means local-agent-mode metadata/path, real user/assistant turns, and no matching Claude Code source path, session id, or fingerprint
- old machine slug `Dominics-Mac-mini` maps to new display name `Dominic's Mac Mini`, and old `Dominics-Macbook` maps to `Dominic's MacBook`, so already-imported historical anchors dedupe against new manifest entries

- [ ] **Step 5a: Specify manifest path and format**

Use JSON and co-locate per-machine manifests with generated markdown as:

```text
/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/manifest-dominics-macbook.json
/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/manifest-dominics-mac-mini.json
```

Each manifest contains entries for one machine only. Each entry includes a `machine` field and `conversation_key`. Commands that need full state load all `manifest-*.json` files and union entries by `(machine, source_path)` and `conversation_key`, so MacBook and Mac Mini paths remain distinct without overwriting each other during sync while cloud-backed exports/caches can still dedupe across machines.

Generated markdown is also machine-separated:

```text
/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-macbook/<product>/<yyyy-mm>.md
/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-mac-mini/<product>/<yyyy-mm>.md
```

Do not write shared markdown filenames directly under `imported-chats/`.

- [ ] **Step 6: Add `.local/` to `.gitignore`**

Add `.local/` in this first task, before any documentation tells an operator to place exports under `.local/chat-exports/`.

- [ ] **Step 7: Run full gate**

Run: `uv run python -m pytest`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats .gitignore
git commit -m "feat: add chat backfill inventory manifest"
```

## Task 2: Claude Code Full-Session Parser

**Files:**
- Create: `src/memsearch/backfill/parsers/__init__.py`
- Create: `src/memsearch/backfill/parsers/claude_code.py`
- Modify: `src/memsearch/backfill/models.py`
- Test: `tests/backfill_chats/test_parse_claude_code.py`

- [ ] **Step 1: Write failing parser tests**

```python
import json
from pathlib import Path

from memsearch.backfill.parsers.claude_code import parse_claude_code


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_claude_code_keeps_user_and_assistant_text(tmp_path: Path):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T10:00:00Z", "message": {"content": "Remember this decision"}},
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-06-01T10:00:01Z", "message": {"content": [{"type": "text", "text": "Decision recorded."}]}},
    ])

    conversation = parse_claude_code(transcript, machine="Test Mac")

    assert conversation.product == "claude_code"
    assert [turn.role for turn in conversation.turns] == ["user", "assistant"]
    assert "Remember this decision" in conversation.turns[0].text


def test_parse_claude_code_omits_tool_results(tmp_path: Path):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T10:00:00Z", "message": {"content": "Debug"}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "SECRET_TOKEN=bad"}]}},
    ])

    conversation = parse_claude_code(transcript, machine="Test Mac")

    assert "SECRET_TOKEN" not in "\n".join(turn.text for turn in conversation.turns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_claude_code.py -v`

Expected: FAIL because parser does not exist.

- [ ] **Step 3: Implement full-session parser**

Wrap or reuse the existing full-session parser in `plugins/claude-code/transcript.py` where possible. That parser already handles all-turn parsing, hook XML stripping, thinking blocks, and tool-result exclusion. If the implementation adds a new parser anyway, document the delta in code comments and tests: backfill needs a product-neutral `Conversation` model and different manifest/rendering metadata.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_claude_code.py -v`

Expected: PASS.

- [ ] **Step 5: Run compatibility tests**

Run: `uv run python -m pytest tests/test_claude_parse_transcript.py tests/backfill_chats/test_parse_claude_code.py -v`

Expected: PASS. Existing hook parser behaviour must remain unchanged.

- [ ] **Step 6: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats
git commit -m "feat: parse claude code backfill sessions"
```

## Task 3: Codex Full-Rollout Parser

**Files:**
- Create: `src/memsearch/backfill/parsers/codex.py`
- Modify: `src/memsearch/backfill/models.py`
- Test: `tests/backfill_chats/test_parse_codex.py`

- [ ] **Step 1: Write failing parser tests**

```python
import json
from pathlib import Path

from memsearch.backfill.parsers.codex import parse_codex_rollout


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_codex_keeps_user_and_agent_messages(tmp_path: Path):
    rollout = tmp_path / "rollout.jsonl"
    write_jsonl(rollout, [
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "Map these files"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "Mapped them."}},
    ])

    conversation = parse_codex_rollout(rollout, machine="Test Mac")

    assert conversation.product == "codex"
    assert [turn.role for turn in conversation.turns] == ["user", "assistant"]
    assert conversation.turns[1].text == "Mapped them."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_codex.py -v`

Expected: FAIL because parser does not exist.

- [ ] **Step 3: Implement Codex parser**

Parse event messages and response-item messages. Skip function calls, tool outputs, reasoning, token counts, and session metadata.

Add at least one fixture row with `response_item` + `message` content blocks for `role: "user"` or `role: "assistant"`, because `plugins/codex/scripts/parse-rollout.sh` documents those real rollout shapes even though its current hook parser skips message duplicates.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_codex.py -v`

Expected: PASS.

- [ ] **Step 5: Run compatibility tests**

Run: `uv run python -m pytest tests/test_codex_parse_rollout.py tests/backfill_chats/test_parse_codex.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats
git commit -m "feat: parse codex backfill sessions"
```

## Task 4: Markdown Renderer and Secret Redaction

**Files:**
- Create: `src/memsearch/backfill/render.py`
- Create: `src/memsearch/backfill/redact.py`
- Modify: `src/memsearch/backfill/models.py`
- Test: `tests/backfill_chats/test_render.py`
- Test: `tests/backfill_chats/test_redact.py`

- [ ] **Step 1: Write failing redaction tests**

```python
from memsearch.backfill.redact import redact_secrets


def test_redact_obvious_tokens():
    text = "Authorization: Bearer sk-test\nOPENAI_API_KEY=abc123"

    redacted = redact_secrets(text)

    assert "sk-test" not in redacted
    assert "abc123" not in redacted
    assert "[REDACTED]" in redacted
```

Add a separate redaction test where a normal user or assistant turn contains a visible bearer/API-key-like value. Expected: parsing retains normal text, `redact_secrets()` removes the secret before render, and the rendered markdown never contains the raw value. Do not rely only on tool-result stripping to prove redaction works.

- [ ] **Step 2: Write failing render tests**

Test that markdown includes:
- `## <Product> session <timestamp/title>`
- HTML comment anchor with source path/export hash.
- Machine and product metadata.
- Turn text after redaction.
- No raw secret values.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/backfill_chats/test_render.py tests/backfill_chats/test_redact.py -v`

Expected: FAIL because modules do not exist.

- [ ] **Step 4: Implement redaction and renderer**

Keep redaction conservative and deterministic. Do not invent summarised facts; render cleaned turns and metadata from parsed source.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/backfill_chats/test_render.py tests/backfill_chats/test_redact.py -v`

Expected: PASS.

- [ ] **Step 6: Run full gate**

Run: `uv run python -m pytest`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats
git commit -m "feat: render redacted chat backfill markdown"
```

## Task 5: Pilot Backfill CLI

**Files:**
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `src/memsearch/backfill/manifest.py`
- Modify: `src/memsearch/backfill/inventory.py`
- Test: `tests/backfill_chats/test_inventory.py`
- Test: `tests/backfill_chats/test_render.py`

- [ ] **Step 1: Write failing CLI tests**

Use `subprocess.run` to execute:

```bash
uv run python -m memsearch.backfill.cli inventory --home <fixture-home> --machine "Test Mac" --json-output
uv run python -m memsearch.backfill.cli pilot --home <fixture-home> --machine "Test Mac" --limit 2 --output <tmpdir>
```

Expected behaviours:
- Inventory emits JSON with product counts.
- Pilot writes markdown and manifest files.
- Re-running pilot does not duplicate already processed source files.
- Running `convert` twice on a fixture home produces byte-identical manifest and markdown output on the second run.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/backfill_chats -v`

Expected: FAIL because CLI commands are incomplete.

- [ ] **Step 3: Implement inventory and pilot commands**

Commands:
- `inventory`
- `pilot`
- `convert`
- `verify-manifest`

Do not call `memsearch index` from conversion commands. Keep conversion and indexing separate so dry-runs are safe.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/backfill_chats -v`

Expected: PASS.

- [ ] **Step 5: Run real read-only inventory on MacBook**

Run:

```bash
uv run python -m memsearch.backfill.cli inventory --home /Users/dominicmonkhouse --machine "Dominic's MacBook" --json-output
```

Expected: counts match or intentionally explain the known inventory:
- Claude Code count is greater than or equal to the known baseline of 1,772 files, unless missing files are explained.
- Codex count is greater than or equal to the known baseline of 228 files, unless missing files are explained.
- Claude Desktop/Cowork local-agent JSONL count is greater than or equal to the known baseline of 403 files, unless missing files are explained.

Higher counts are expected when new sessions have been created since plan writing. Treat zero counts or unexplained drops below baseline as problems.

- [ ] **Step 6: Run full gate**

Run: `uv run python -m pytest`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats
git commit -m "feat: add chat backfill pilot cli"
```

## Task 6: Claude Desktop/Cowork Parser

**Files:**
- Create: `src/memsearch/backfill/parsers/claude_desktop.py`
- Modify: `src/memsearch/backfill/cli.py`
- Test: `tests/backfill_chats/test_parse_claude_desktop.py`

- [ ] **Step 1: Sample formats read-only**

Read representative files from:
- `/Users/dominicmonkhouse/Library/Application Support/Claude/local-agent-mode-sessions/**/*.jsonl`
- `/Users/dominicmonkhouse/Library/Application Support/Claude/local-agent-mode-sessions/**/*.json`
- `/Users/dominicmonkhouse/Library/Application Support/Claude/claude-code-sessions/**/*.json`

Expected: identify which file shapes contain actual user/assistant turns and which are audit/config/plugin files.

Also compare sampled `claude-code-sessions` records against `~/.claude/projects` and existing historical markdown anchors. If a record is a Claude Code mirror or wrapper around an already-imported transcript, mark it `possible_duplicate_claude_code` or `already_imported`, not converted.

Define Cowork-only before implementing conversion. Cowork-only requires:
- file path or metadata identifying `local-agent-mode-sessions`, not `claude-code-sessions`
- proven user/assistant turns in the sampled shape
- no matching Claude Code source path, session id, historical anchor, or normalised transcript fingerprint

If any of those checks is missing, skip with reason `possible_duplicate_claude_code` or `unknown_format`.

- [ ] **Step 2: Write fixture tests from sampled shapes**

Fixture tests must prove:
- User/assistant text is retained.
- Audit logs are excluded.
- Plugin/dependency files are excluded.
- Tool output and secret-like values are not rendered.
- Subagent transcripts are excluded unless explicitly enabled.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_claude_desktop.py -v`

Expected: FAIL because parser is incomplete.

- [ ] **Step 4: Implement parser**

Parse only proven conversation-bearing shapes. If a JSON shape is unknown, record a skipped manifest entry with reason `unknown_format`, not a guessed conversion.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_claude_desktop.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats
git commit -m "feat: parse claude desktop cowork sessions"
```

## Task 7: Official Export Parsers

**Files:**
- Create: `src/memsearch/backfill/parsers/chatgpt_export.py`
- Create: `src/memsearch/backfill/parsers/claude_export.py`
- Modify: `src/memsearch/backfill/inventory.py`
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `.gitignore`
- Test: `tests/backfill_chats/test_parse_chatgpt_export.py`
- Test: `tests/backfill_chats/test_parse_claude_export.py`
- Create: `docs/backfill-chat-sources.md`

- [ ] **Step 1: Confirm official export samples exist**

Before implementing export parsers, confirm the required official exports have been downloaded and placed under:

```text
/Users/dominicmonkhouse/Projects/memsearch/.local/chat-exports/
```

Expected files:
- ChatGPT export zip or extracted folder containing `conversations.json` or `chat.html`.
- Claude export zip or extracted folder containing conversation JSON/HTML.

If either ChatGPT or Claude export sample is unavailable, stop this task and record the blocker in `docs/backfill-chat-sources.md`; do not guess the export shape.

- [ ] **Step 2: Document export placement**

Document that official export zips should be placed outside git, proposed path:

```text
/Users/dominicmonkhouse/Projects/memsearch/.local/chat-exports/
```

Verify `.local/` is already present in `.gitignore` from Task 1 before any export archive is placed there.

- [ ] **Step 3: Write fixture tests for ChatGPT export**

Cover `conversations.json` if present and `chat.html` fallback. Expected: turn ordering, title, timestamps, and conversation id are preserved.

Add a fixture where the same ChatGPT conversation id exists in an official export and a desktop `.data` cache file. Expected: the export is parsed and the cache item is marked `shadowed_by_export`.

- [ ] **Step 4: Write fixture tests for Claude export**

Cover the official Claude export shape once a sample is available. Until then, mark unknown shape as skipped with a clear manifest reason.

Add a fixture where the same Claude conversation id exists in an official export and Chrome IndexedDB cache. Expected: the export is parsed and the cache item is marked `shadowed_by_export`.

- [ ] **Step 5: Implement parsers**

Prefer structured JSON over HTML. HTML parsing must use stdlib `html.parser` or a dependency already present in the repo; do not add dependencies unless the fixture proves stdlib is insufficient.

- [ ] **Step 6: Run parser tests**

Run:

```bash
uv run python -m pytest tests/backfill_chats/test_parse_chatgpt_export.py tests/backfill_chats/test_parse_claude_export.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats docs/backfill-chat-sources.md .gitignore
git commit -m "feat: parse official chat exports"
```

## Task 8: Manus Probe and Deferred Parser

**Files:**
- Create: `src/memsearch/backfill/parsers/manus.py`
- Modify: `src/memsearch/backfill/inventory.py`
- Modify: `docs/backfill-chat-sources.md`
- Test: `tests/backfill_chats/test_parse_manus.py`

- [ ] **Step 1: Search for official route**

Check Manus documentation and app UI for export/API support before relying on local IndexedDB.

Expected: plan records official route if found; otherwise Manus remains a cache-probe source.

- [ ] **Step 2: Write probe tests**

Test that Manus files can be inventoried and classified as `indexeddb`, `cache`, or `unknown`, without pretending unknown cache blobs are conversations.

If a Manus conversation id or transcript fingerprint appears on both MacBook and Mac Mini, verify only one generated conversation is emitted and the other manifest entry is marked `duplicate_conversation`.

- [ ] **Step 3: Implement probe-only parser**

Parser returns skipped manifest entries unless a proven conversation shape exists.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/backfill_chats/test_parse_manus.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/memsearch/backfill tests/backfill_chats docs/backfill-chat-sources.md
git commit -m "feat: inventory manus chat sources"
```

## Task 9: Real Pilot and Memsearch Verification

**Files:**
- Modify: `docs/backfill-chat-sources.md`
- Generated only, not committed: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/<run-id>/`

- [ ] **Step 1: Run MacBook pilot conversion**

Pilots write to a run-specific quarantine directory, not to the canonical imported-chat root. Do not index a pilot into the production collection. Use a pilot collection only if search verification is needed.

Run:

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)
uv run python -m memsearch.backfill.cli pilot \
  --home /Users/dominicmonkhouse \
  --machine "Dominic's MacBook" \
  --limit 10 \
  --output "/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/$RUN_ID"
```

Expected: markdown and manifest are written for up to 10 source conversations per supported source, with skipped entries for unsupported shapes.

- [ ] **Step 2: Run Mac Mini pilot inventory**

Mini execution is SSH-driven from the MacBook. Before running any Mini inventory or conversion command, verify the Mini repo, `uv`, and package import:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && command -v uv'
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && uv run python -c "import memsearch.backfill"'
```

Expected: both commands exit 0. If either fails, sync/update the Mini checkout or PATH and rerun this preflight before continuing.

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && uv run python -m memsearch.backfill.cli inventory --home /Users/dominicmonkhouse --machine "Dominic'\''s Mac Mini" --json-output'
```

Expected: counts match the known Mini inventory or explain drift.

- [ ] **Step 3: Run Mac Mini pilot conversion**

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && uv run python -m memsearch.backfill.cli pilot --home /Users/dominicmonkhouse --machine "Dominic'\''s Mac Mini" --limit 10 --output "/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/'"$RUN_ID"'"'
```

Expected: generated markdown on the Mini is available to the shared memory/index path used by Memsearch, or the command reports that output synchronisation is missing.

- [ ] **Step 4: Copy Mini pilot output back to MacBook**

Run from the MacBook:

```bash
rsync -av "dom-kamet.tailf78a36.ts.net:/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/$RUN_ID/" \
  "/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/$RUN_ID/"
```

Expected: Mini-generated markdown and `manifest-dominics-mac-mini.json` are present in the MacBook pilot run directory. The MacBook manifest is not overwritten because each machine writes a separate manifest filename.

- [ ] **Step 5: Derive the active collection name**

Run:

```bash
bash plugins/claude-code/scripts/derive-collection.sh /Users/dominicmonkhouse/Projects/memsearch
```

Expected: returns the collection to use in all following commands. During plan writing this was `ms_memsearch_ae2d4f9b`; execution must derive it rather than hardcoding it.

- [ ] **Step 6: Verify collection identity, Milvus, and scan generated markdown before pilot indexing**

Run:

```bash
COLLECTION=$(bash plugins/claude-code/scripts/derive-collection.sh /Users/dominicmonkhouse/Projects/memsearch)
memsearch stats --collection "$COLLECTION"
memsearch search "backfill-agent:codex" --top-k 5 --json-output --collection "$COLLECTION" | tee /tmp/memsearch-backfill-collection-check.json
RUN_ID="$RUN_ID" uv run python - <<'PY'
from pathlib import Path
import os
import re

root = Path("/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs") / os.environ["RUN_ID"]
pattern = re.compile(r"sk-[A-Za-z0-9]|Authorization: Bearer|OPENAI_API_KEY|ANTHROPIC_API_KEY|password=", re.I)
matches = []
for path in root.rglob("*.md"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if pattern.search(text):
        matches.append(str(path))
if matches:
    raise SystemExit("Potential secrets found before indexing:\n" + "\n".join(matches))
PY
```

Expected: Milvus responds, the collection check returns existing historical memory context from `.memsearch/memory/historical-sessions`, and no secret matches are found in the pilot run directory. If the collection check does not show the intended historical memory collection, hard stop. If secrets are found, stop before indexing, fix redaction/parser behaviour, regenerate affected markdown, and rerun the scan.

- [ ] **Step 7: Optionally index the pilot into a pilot collection**

Do this only if search verification is needed before pilot acceptance. Never index pilot markdown into the production collection.

```bash
PILOT_COLLECTION="${COLLECTION}_pilot_${RUN_ID//-/}"
memsearch index "/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/pilot-runs/$RUN_ID" --collection "$PILOT_COLLECTION"
```

Expected: command completes without Milvus errors and indexes only pilot markdown chunks into the pilot collection.

- [ ] **Step 8: Verify recall**

Run three searches against known pilot phrases:

```bash
SEARCH_COLLECTION="$PILOT_COLLECTION"
memsearch search "Claude Desktop Cowork local agent" --top-k 5 --json-output --collection "$SEARCH_COLLECTION"
memsearch search "ChatGPT export" --top-k 5 --json-output --collection "$SEARCH_COLLECTION"
memsearch search "Manus IndexedDB" --top-k 5 --json-output --collection "$SEARCH_COLLECTION"
```

Expected: if Step 7 was used, run these against `$PILOT_COLLECTION` and results include generated imported-chat markdown where relevant; no raw tool dumps or secrets appear. If Step 7 was skipped, verify the same phrases by inspecting the generated pilot markdown directly.

If pilot output is rejected, do not promote it and do not index it into the production collection. Leave the quarantined pilot run in place for review, or move generated pilot files to `~/.Trash/` only after explicit approval and with the exact file list stated first. Source transcript/cache files are never deleted.

- [ ] **Step 9: Document pilot result**

Update `docs/backfill-chat-sources.md` with:
- source counts
- parsed counts
- skipped counts and reasons
- index command used
- sample search phrases and result status

- [ ] **Step 10: Run full gate**

Run: `uv run python -m pytest`

Expected: PASS.

- [ ] **Step 11: Commit docs and code only**

```bash
git add src/memsearch/backfill tests/backfill_chats docs/backfill-chat-sources.md
git commit -m "docs: record chat backfill pilot verification"
```

## Task 10: Full Backfill Run

**Files:**
- Generated only, not committed: `/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/`
- Per-machine generated manifest files under the same output tree.

- [ ] **Step 1: Confirm pilot acceptance**

Do not run full conversion until pilot output has been reviewed and searches have passed.

- [ ] **Step 2: Run full MacBook conversion**

Run:

```bash
uv run python -m memsearch.backfill.cli convert \
  --home /Users/dominicmonkhouse \
  --machine "Dominic's MacBook" \
  --output /Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats
```

Expected: all supported MacBook sources are converted or explicitly skipped in the manifest.

- [ ] **Step 3: Run full Mac Mini conversion**

Before converting on the Mini, verify the package import still works:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && command -v uv'
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && uv run python -c "import memsearch.backfill"'
```

Expected: both commands exit 0. If either fails, sync/update the Mini checkout or PATH and rerun this preflight before continuing.

Run:

```bash
ssh dom-kamet.tailf78a36.ts.net 'cd /Users/dominicmonkhouse/Projects/memsearch && uv run python -m memsearch.backfill.cli convert --home /Users/dominicmonkhouse --machine "Dominic'\''s Mac Mini" --output /Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats'
```

Expected: all supported Mac Mini sources are converted or explicitly skipped in the manifest.

- [ ] **Step 4: Copy Mini output back to MacBook**

Run from the MacBook:

```bash
rsync -av dom-kamet.tailf78a36.ts.net:/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/ \
  /Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/
```

Expected: the MacBook output directory includes both MacBook and Mac Mini generated markdown before indexing. `manifest-dominics-macbook.json` and `manifest-dominics-mac-mini.json` both exist, and neither has overwritten the other.

- [ ] **Step 5: Derive the active collection name**

Run:

```bash
COLLECTION=$(bash plugins/claude-code/scripts/derive-collection.sh /Users/dominicmonkhouse/Projects/memsearch)
echo "$COLLECTION"
```

Expected: returns the active collection name. During plan writing this was `ms_memsearch_ae2d4f9b`; execution must not assume that literal value.

- [ ] **Step 6: Verify collection identity, Milvus, and scan generated markdown before indexing**

Run:

```bash
memsearch stats --collection "$COLLECTION"
memsearch search "backfill-agent:codex" --top-k 5 --json-output --collection "$COLLECTION" | tee /tmp/memsearch-backfill-collection-check.json
uv run python - <<'PY'
from pathlib import Path
import re

roots = [
    Path("/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-macbook"),
    Path("/Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-mac-mini"),
]
pattern = re.compile(r"sk-[A-Za-z0-9]|Authorization: Bearer|OPENAI_API_KEY|ANTHROPIC_API_KEY|password=", re.I)
matches = []
for root in roots:
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            matches.append(str(path))
if matches:
    raise SystemExit("Potential secrets found before indexing:\n" + "\n".join(matches))
PY
```

Expected: Milvus responds, the collection check returns existing historical memory context from `.memsearch/memory/historical-sessions`, and no secret matches are found. If the collection check does not show the intended historical memory collection, hard stop. If secrets are found, stop before indexing, fix redaction/parser behaviour, regenerate affected markdown, and rerun the scan.

- [ ] **Step 7: Index generated markdown**

Run:

```bash
memsearch index /Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-macbook --collection "$COLLECTION"
memsearch index /Users/dominicmonkhouse/Projects/.memsearch/memory/imported-chats/dominics-mac-mini --collection "$COLLECTION"
```

Expected: indexing completes for both production machine directories and `memsearch stats --collection "$COLLECTION"` reports increased chunks. `pilot-runs/` is never indexed into the production collection.

- [ ] **Step 8: Verify recall**

Run targeted searches for known phrases from each source type.

Expected: search results return useful imported memories from supported sources.

- [ ] **Step 9: Final manifest report**

Generate a final report with:
- total files discovered by source and machine
- parsed conversations
- skipped files by reason
- markdown files generated
- indexing status
- sample search verification

## Risks and Mitigations

- **Duplicate indexing:** Use source path/content hash manifest and deterministic markdown anchors. Re-running conversion must not duplicate sections.
- **Duplicate ingestion:** Build the `already_imported` set from both the old manifest and old historical markdown anchors. Dedupe by platform conversation id where available, then by normalised transcript fingerprint. Treat official exports as canonical and cache/IndexedDB records as fallback or shadow copies.
- **Secret leakage:** Redact before writing markdown, then grep generated output before indexing.
- **Cache brittleness:** Treat IndexedDB/cache as fallback. Prefer official exports for ChatGPT and Claude Chat.
- **Source confusion:** Keep product labels distinct: Claude Code, Codex, Claude Desktop/Cowork, Claude Chat, ChatGPT, Manus.
- **Mac Mini drift:** Run source inventory on the Mini before conversion. Do not assume MacBook counts apply.
- **Manifest clobbering:** Use per-machine manifest filenames so `rsync` cannot overwrite MacBook state with Mini state. Full-state checks read all `manifest-*.json` files.
- **Milvus/index risk:** Do not reset collections. Check `memsearch stats --collection "$COLLECTION"` before indexing and index generated markdown only after pilot review and secret scan.
- **Generated markdown collisions:** Generated markdown paths include the machine slug. `rsync` must not be able to overwrite MacBook markdown with Mini markdown.
- **Transcript noise:** Exclude tool outputs, audit logs, subagents by default, plugin bundles, dependency folders, and generated code caches.
