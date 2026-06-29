# Antigravity MemSearch Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Antigravity/Gemini session capture lane so Antigravity chat history is rendered into MemSearch-ready Markdown cards before Gemini's local session retention deletes it.

**Architecture:** Extend the existing MemSearch backfill package rather than creating a parallel exporter. Treat Gemini/Antigravity chat JSON under `~/.gemini/tmp/*/chats/*.json` as the source, render compact session cards into the shared Markdown memory lane, and use the existing `source-sync`, state, secret-scan, scheduler, freshness, and optional indexing patterns already used for Linear and Manus. Do not use Hermes as the capture mechanism: Hermes is runtime memory infrastructure, while this plan captures Antigravity's own session history into MemSearch.

**Tech Stack:** Python 3.10+, Click CLI, MemSearch Markdown cards, local Gemini/Antigravity session JSON, existing `memsearch.backfill` parser/render/source-sync modules, pytest, ruff, LaunchAgent plist renderer.

---

## Current evidence

- Memory recall found this is a missing lane: Antigravity parity exists under MON-451, but Antigravity-to-MemSearch capture is not yet implemented.
- Current clean target repo: `/Users/dominicmonkhouse/Projects/memsearch` on `main`.
- Existing backfill package: `/Users/dominicmonkhouse/Projects/memsearch/src/memsearch/backfill/`.
- Existing tests: `/Users/dominicmonkhouse/Projects/memsearch/tests/backfill_chats/`.
- Existing source freshness docs: `/Users/dominicmonkhouse/Projects/memsearch/docs/source-freshness-automation.md`.
- Existing source backfill docs: `/Users/dominicmonkhouse/Projects/memsearch/docs/backfill-chat-sources.md`.
- Local official Gemini CLI docs state that session history is saved automatically, includes prompts, model responses, tool executions, token usage and summaries, and lives in `~/.gemini/tmp/<project_hash>/chats/`.
- Local official Gemini CLI docs state session retention defaults to 30 days.
- Local observed Antigravity/Gemini files exist at `/Users/dominicmonkhouse/.gemini/tmp/new-project/chats/session-*.json`.
- Observed session JSON shape: top-level `sessionId`, `projectHash`, `startTime`, `lastUpdated`, `kind`, and `messages`; message objects include `id`, `type`, `timestamp`, `content`, and sometimes `displayContent`.
- `~/.gemini/antigravity-cli/cache/last_conversations.json` is only a project-path to conversation-id cache. It is useful metadata, not the transcript source.

## Not included in this version

- **Hermes runtime changes:** Not included. Hermes affects Hermes-native runtime behaviour; it does not capture Antigravity chat JSON into MemSearch.
- **Antigravity desktop parity fixes:** Not included. MON-451 owns MCP, Linear, Open Brain, hooks, skill execution, and handoff parity.
- **Raw full-log indexing:** Not included. Like Manus, raw logs are too noisy and may include tool payloads. This version indexes compact cards only.
- **Installing LaunchAgents:** Not included. The scheduler renderer may create a plist, but installation remains approval-gated.
- **Editing Gemini retention settings:** Not included. We will capture daily instead of changing retention policy silently.
- **Backfilling deleted sessions:** Not possible unless the files still exist. This plan only captures files present under `~/.gemini/tmp/`.

## File structure

- Create `src/memsearch/backfill/parsers/gemini.py`: parse Gemini/Antigravity chat JSON into `Conversation`.
- Create `src/memsearch/backfill/gemini_cards.py`: render compact MemSearch cards from parsed Gemini sessions.
- Modify `src/memsearch/backfill/inventory.py`: add a `gemini_cli_chat` inventory rule for `.gemini/tmp/*/chats/*.json`.
- Modify `src/memsearch/backfill/cli.py`: add parser support plus `antigravity-cards` and `source-sync antigravity` commands.
- Modify `src/memsearch/backfill/source_sync.py`: add `sync_antigravity` using existing state, lock, scan, and optional indexing patterns.
- Modify `src/memsearch/backfill/freshness.py`: include Antigravity in source freshness reporting and proof-search previews.
- Modify `src/memsearch/backfill/scheduler.py`: render a daily Antigravity source-sync plist without installing it.
- Modify `docs/backfill-chat-sources.md`: document the Antigravity/Gemini route, safety gates, and first-run review indexing.
- Modify `docs/source-freshness-automation.md`: document cadence, state, dry-run, daily sync, and scheduler output.
- Create `tests/backfill_chats/test_parse_gemini.py`: parser coverage for observed Gemini JSON.
- Create `tests/backfill_chats/test_gemini_cards.py`: card rendering and secret redaction coverage.
- Modify `tests/backfill_chats/test_source_sync.py`: dry-run, changed-session detection, state update, and optional indexing tests.
- Modify `tests/backfill_chats/test_freshness.py`: Antigravity appears in the freshness report.
- Modify `tests/backfill_chats/test_scheduler.py`: daily Antigravity plist is rendered but not installed.

## Acceptance checks

- `uv run python -m memsearch.backfill.cli inventory --machine "$(scutil --get ComputerName)" --json-output` reports `gemini_cli_chat` when local Gemini session files exist.
- `uv run python -m memsearch.backfill.cli source-sync antigravity --machine "$(scutil --get ComputerName)" --dry-run --max-sessions 5` previews changed sessions without writing state.
- A non-dry Antigravity sync writes Markdown cards under `<memory_root>/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli/`, where `<memory_root>` defaults to `Path.home() / "Projects" / ".memsearch" / "memory"`.
- Secret scans run against rendered card Markdown before success is reported.
- `source-freshness` reports Linear, Manus, and Antigravity.
- Scheduler rendering creates `com.memsearch.daily-antigravity-sync.plist` and still does not install it.
- Tests pass for new parser/card/source-sync/freshness/scheduler coverage.
- Full project verification passes: `uv run ruff check src tests` and `uv run pytest`.

The `scutil` commands are live macOS acceptance checks for Dom's machine. Unit tests must use fixture machine names such as `"test-machine"` and must not depend on `scutil`.

## Risks and decisions

- **Retention risk:** Gemini defaults to 30-day session retention, so daily sync is the right cadence. Weekly is too slow for a tool that may be used heavily during credit balancing.
- **Schema drift:** Gemini/Antigravity JSON is local app state, not a published stable export schema. Parser tests must use fixtures based on observed files and tolerate extra fields.
- **Privacy and payload risk:** Tool output can appear in session logs. Cards should store concise request/outcome/tool-hint snippets and a pointer back to the local JSON, not full raw payloads.
- **Indexing risk:** First canonical indexing should be a manual review flow: dry-run, card inspection, temporary review collection, proof search, then canonical indexing.
- **Old worktree risk:** `/Users/dominicmonkhouse/Projects/memsearch-chat-backfill` has uncommitted historical work and must not be used for this implementation unless a separate reconciliation task approves it.

## Task 1: Add Gemini parser

**Files:**
- Create: `src/memsearch/backfill/parsers/gemini.py`
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `src/memsearch/backfill/inventory.py`
- Create: `tests/backfill_chats/test_parse_gemini.py`

- [ ] **Step 1: Write parser fixture tests**

Create test fixtures inline in `tests/backfill_chats/test_parse_gemini.py` using the observed shape:

```python
payload = {
    "sessionId": "416d9ae3-b800-4f8e-bc96-549f521041e9",
    "projectHash": "c99376fd827c64f7fd4f1ef825401a6a62521b12ef65ca8d27afec3056c024ef",
    "startTime": "2026-06-27T07:57:35.868Z",
    "lastUpdated": "2026-06-27T07:57:46.926Z",
    "kind": "main",
    "messages": [
        {"id": "u1", "type": "user", "timestamp": "2026-06-27T07:57:35.900Z", "content": "Use memory-recall."},
        {"id": "a1", "type": "assistant", "timestamp": "2026-06-27T07:57:46.000Z", "content": "I found the relevant memory."},
    ],
}
```

Expected assertions:
- `conversation.product == "gemini_cli_chat"`.
- `conversation.platform_id` is the `sessionId`.
- `conversation.started_at` and `conversation.ended_at` are populated.
- User and assistant turns are preserved with timestamps.
- Metadata includes `project_hash`, `kind`, `message_count`, and `source_format`.

- [ ] **Step 2: Run the parser test to verify it fails**

Run:

```bash
uv run pytest tests/backfill_chats/test_parse_gemini.py -q
```

Expected: FAIL because `memsearch.backfill.parsers.gemini` does not exist.

- [ ] **Step 3: Implement `parse_gemini_chat`**

Implement:

```python
def parse_gemini_chat(path: str | Path, *, machine: str) -> Conversation:
    ...
```

Rules:
- Read UTF-8 JSON.
- Require a top-level dict and tolerate unknown keys.
- Extract `messages` when it is a list.
- Map message `type` values into `Turn.role` as lower-case strings.
- Prefer `displayContent` over `content` only when `content` is absent or non-text. Treat `content` as non-text if it is not a `str`; in that case use `displayContent` if it is a `str`, otherwise fall back to the shared text-extraction helper for `content`.
- Flatten string/list/dict content conservatively, following the existing `_extract_text` style in `models.py`.
- Set `platform_id=sessionId`.
- Set `title` from the first non-empty user message, truncated to 120 characters.
- Set `started_at=startTime` and `ended_at=lastUpdated`.
- Store metadata: `project_hash`, `kind`, `message_count`, `last_updated`, and `source_format="gemini_cli_chat_json_v1"`. `conversation.ended_at` must also be set to the same `lastUpdated` value so renderers can use the common `Conversation` field, while source-sync can use `metadata["last_updated"]` for explicit snapshot logic.

- [ ] **Step 4: Add inventory and convert support**

Modify `inventory.py`:

```python
InventoryRule("gemini_cli_chat", ".gemini/tmp/*/chats/*.json")
```

Modify `cli.py`:
- Import `parse_gemini_chat`.
- In `_parse_source`, route `source.product == "gemini_cli_chat"` to `parse_gemini_chat`.

- [ ] **Step 5: Run parser and inventory tests**

Run:

```bash
uv run pytest tests/backfill_chats/test_parse_gemini.py tests/backfill_chats/test_inventory.py -q
```

Expected: PASS.

## Task 2: Render compact Antigravity cards

**Files:**
- Create: `src/memsearch/backfill/gemini_cards.py`
- Create: `tests/backfill_chats/test_gemini_cards.py`
- Modify: `src/memsearch/backfill/cli.py`

- [ ] **Step 1: Write failing card tests**

Cover:
- Card contains a heading with session start time and title.
- Anchor includes `backfill-agent:antigravity`, `source:gemini_cli_chat`, `session:<sessionId>`, `project_hash:<hash>`, and `machine:<slug>`.
- Card includes compact fields: session ID, project hash, source path, message count, user prompt excerpt, assistant outcome excerpt, and tool/message type hints.
- Card redacts secrets through `redact_secrets`.
- Full raw message payload is not dumped.
- `card-manifest.json` is written and includes `session_ids`, `source_paths`, `card_count`, and `card_format="antigravity_gemini_session_card_v1"`.
- The `antigravity-cards --input <file>` path accepts a single `session-*.json` file and writes one card.

- [ ] **Step 2: Run card tests to verify failure**

Run:

```bash
uv run pytest tests/backfill_chats/test_gemini_cards.py -q
```

Expected: FAIL because `gemini_cards.py` does not exist.

- [ ] **Step 3: Implement card rendering**

Implement:

```python
def render_gemini_session_card(conversation: Conversation) -> str:
    ...

def write_gemini_cards(conversations: list[Conversation], output_dir: Path, *, machine: str, force: bool = False) -> dict[str, Any]:
    ...
```

Card content:
- `## Antigravity session <startTime>: <title>`
- HTML anchor with session and source fields.
- Bullets for machine, project hash, source file, session ID, message count, time range.
- `### User request` containing the first user turn excerpt.
- `### Assistant outcome` containing the last assistant turn excerpt.
- `### Conversation signals` containing message role counts and notable types.
- No full raw tool output.

Write path:

```text
<output_dir>/memory/antigravity/gemini_cli/<yyyy-mm>.md
```

`output_dir` here is the run-scoped card directory passed by `source-sync`, i.e. `<memory_root>/antigravity/gemini-cli/<run_id>/cards`. The standalone `antigravity-cards` command may pass any explicit output directory, but it uses the same internal `memory/antigravity/gemini_cli/` layout.

Bucket cards by each session's own `started_at` month, not the run-start month, so first backfills spanning a month boundary append each session to the correct `<yyyy-mm>.md` file.

Manifest:

```text
<output_dir>/card-manifest.json
```

The manifest is always written at exactly `<output_dir>/card-manifest.json`, the same directory passed as `output_dir`, not inside the nested `memory/antigravity/gemini_cli/` card path. Tests must assert both the manifest fields and this manifest location.

Manifest fields:
- `session_ids`
- `source_paths`
- `card_count`
- `card_format = "antigravity_gemini_session_card_v1"`

- [ ] **Step 4: Add CLI command**

Add:

```bash
uv run python -m memsearch.backfill.cli antigravity-cards --input <session-json-dir-or-file> --machine <machine> --output <dir> --force
```

This command should parse one file or all `*.json` files under a directory and write cards.

Directory input is intentionally non-recursive: parse only direct child `*.json` files. Canonical recursive discovery belongs to `source-sync antigravity`, which scans `~/.gemini/tmp/*/chats/*.json`.

- [ ] **Step 5: Run card tests**

Run:

```bash
uv run pytest tests/backfill_chats/test_gemini_cards.py -q
```

Expected: PASS.

## Task 3: Add source-sync antigravity

**Files:**
- Modify: `src/memsearch/backfill/source_sync.py`
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `tests/backfill_chats/test_source_sync.py`

- [ ] **Step 1: Write failing source-sync tests**

Add tests for:
- Dry-run without prior state reports changed sessions and does not write `antigravity.json`.
- Non-dry sync parses selected session files, writes cards, scans cards, and updates state.
- State uses source-path plus content hash snapshots, so unchanged sessions are skipped on the next run.
- Refactoring defaults preserves existing Linear and Manus output roots: `DEFAULT_LINEAR_OUTPUT_ROOT` still resolves to `Path.home() / "Projects" / ".memsearch" / "memory" / "linear"` and `DEFAULT_MANUS_CARD_ROOT` still resolves to `Path.home() / "Projects" / ".memsearch" / "memory" / "manus-cloud" / "manus-api"`.
- `--since` filters by `lastUpdated` or file mtime when `lastUpdated` is absent.
- A fixture with `lastUpdated` absent proves the `--since` fallback uses file mtime.
- `--since` accepts ISO 8601 date or timestamp strings, matching the existing source-sync convention. Tests should cover at least a full timestamp such as `2026-06-26T00:00:00Z`; relative strings such as `24h` are not part of this plan.
- Optional indexing calls `index_markdown_cards` only when `--index` is set.
- Secret scan failure on rendered card Markdown raises and records no success state. Do not scan the raw Gemini JSON in this source-sync path; raw logs may contain noisy tool payloads.

- [ ] **Step 2: Run source-sync tests to verify failure**

Run:

```bash
uv run pytest tests/backfill_chats/test_source_sync.py -q
```

Expected: FAIL for missing `sync_antigravity`.

- [ ] **Step 3: Implement discovery helpers**

In `source_sync.py`, add helpers:

```python
def _discover_gemini_chat_sources(home: Path, machine: str, max_sessions: int | None = None) -> list[SourceFile]:
    ...

def _gemini_session_snapshots(conversations: list[Conversation]) -> dict[str, str]:
    ...
```

Snapshot key:
- Absolute source path string.

Snapshot value:
- Prefer `conversation.metadata["last_updated"]` plus `source.content_hash`.
- Fall back to source content hash only.

- [ ] **Step 4: Implement `sync_antigravity`**

Signature:

```python
def sync_antigravity(
    *,
    machine: str,
    home: Path = Path.home(),
    since: str | None = None,
    output_root: Path = DEFAULT_ANTIGRAVITY_CARD_ROOT,
    state_dir: Path = Path(".local/source-sync-state"),
    dry_run: bool = False,
    index: bool = False,
    collection: str = "memsearch_chunks",
    max_sessions: int | None = None,
) -> SyncSummary:
    ...
```

Default output root:

```python
DEFAULT_MEMSEARCH_MEMORY_ROOT = Path.home() / "Projects" / ".memsearch" / "memory"
DEFAULT_LINEAR_OUTPUT_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "linear"
DEFAULT_MANUS_CARD_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "manus-cloud" / "manus-api"
DEFAULT_ANTIGRAVITY_CARD_ROOT = DEFAULT_MEMSEARCH_MEMORY_ROOT / "antigravity" / "gemini-cli"
```

Refactor the existing Linear and Manus defaults onto the shared `DEFAULT_MEMSEARCH_MEMORY_ROOT` in the same edit so Antigravity does not introduce another one-off absolute path.

Keep `state_dir=Path(".local/source-sync-state")` aligned with the existing Linear and Manus repo-local state pattern, but make the runtime contract explicit: scheduler plists must set `WorkingDirectory` to the repo root and shell commands must `cd` to the repo root before invoking `source-sync`. CLI help/docs must say that callers outside the repo root should pass `--state-dir` explicitly, and the CLI should warn or fail rather than silently creating default state under an unrelated current directory.

Steps tuple:
- discover Gemini chat files
- parse changed sessions
- render compact cards
- scan cards
- update state
- optional index

Index path:

```text
<card_root>/memory/antigravity/gemini_cli
```

For freshness reporting, `_card_root("antigravity", memory_root)` should return the run-parent root `<memory_root>/antigravity/gemini-cli`; `_count_markdown_cards` already walks recursively, so it will count Markdown cards under each `<run_id>/cards/memory/antigravity/gemini_cli/` directory.

- [ ] **Step 5: Wire CLI command**

Add:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity \
  --machine "$(scutil --get ComputerName)" \
  --dry-run \
  --max-sessions 5
```

Options:
- `--home`
- `--since`
- `--output-root`
- `--state-dir`
- `--dry-run`
- `--index`
- `--collection`
- `--max-sessions`

`--home` defaults to `Path.home()`. The acceptance-check commands intentionally omit it and therefore scan the current user's `~/.gemini/tmp/*/chats/*.json`.

`--since` accepts ISO 8601 date or timestamp strings only, following the existing source-sync convention.

- [ ] **Step 6: Run source-sync tests**

Run:

```bash
uv run pytest tests/backfill_chats/test_source_sync.py -q
```

Expected: PASS.

## Task 4: Add freshness and scheduler support

**Files:**
- Modify: `src/memsearch/backfill/freshness.py`
- Modify: `src/memsearch/backfill/scheduler.py`
- Modify: `tests/backfill_chats/test_freshness.py`
- Modify: `tests/backfill_chats/test_scheduler.py`

- [ ] **Step 1: Write failing freshness test**

Update `test_freshness.py` to assert the report includes:

```json
{"source": "antigravity", "next_run": "daily at 06:40 local"}
```

Card root should resolve to:

```text
<memory_root>/antigravity/gemini-cli
```

- [ ] **Step 2: Write failing scheduler test**

Update `test_scheduler.py` to assert:
- `com.memsearch.daily-antigravity-sync.plist` exists.
- `StartCalendarInterval` is `{"Hour": 6, "Minute": 40}`.
- Program arguments include `source-sync antigravity --index`.
- `WorkingDirectory` is the repo root so the repo-local `.local/source-sync-state` contract is honoured.
- Summary still reports `installed: false` and `approval_required_before_install: true`.

- [ ] **Step 3: Implement freshness support**

Modify `source_freshness_report` to include `_source_report("antigravity", ...)`.

Modify `_card_root` and `next_run` logic to handle three sources explicitly.

- [ ] **Step 4: Implement scheduler support**

Add a rendered plist:

```text
.local/launchagents/com.memsearch.daily-antigravity-sync.plist
```

Command:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity --machine <machine> --index
```

Cadence:
- Daily 06:40 local, after Linear at 06:30 and before proof checks.

- [ ] **Step 5: Run freshness and scheduler tests**

Run:

```bash
uv run pytest tests/backfill_chats/test_freshness.py tests/backfill_chats/test_scheduler.py -q
```

Expected: PASS.

## Task 5: Update documentation and first-run safety procedure

**Files:**
- Modify: `docs/backfill-chat-sources.md`
- Modify: `docs/source-freshness-automation.md`

- [ ] **Step 1: Update `docs/backfill-chat-sources.md`**

Add section:

```markdown
## Antigravity / Gemini route
```

Include:
- Source path: `~/.gemini/tmp/*/chats/*.json`.
- `last_conversations.json` is a cache/id map only, not the transcript source.
- Sessions default to 30-day retention.
- Raw logs are not indexed directly.
- Cards are the MemSearch source.
- Commands for dry-run, one-off sync, card scan, and temporary review indexing.

- [ ] **Step 2: Update `docs/source-freshness-automation.md`**

Add:
- Cadence: Antigravity daily at 06:40.
- State: `.local/source-sync-state/antigravity.json`.
- Dry-run command.
- Daily command.
- First-run review collection command.
- Scheduler output path.

- [ ] **Step 3: Run docs grep check**

Run:

```bash
rg -n "Antigravity|Gemini|antigravity|gemini-cli|daily at 06:40" docs/backfill-chat-sources.md docs/source-freshness-automation.md
```

Expected: all new Antigravity sections are findable.

## Task 6: Verify locally against real Antigravity files

**Files:**
- No source edits unless tests expose a bug in earlier tasks.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
uv run pytest \
  tests/backfill_chats/test_parse_gemini.py \
  tests/backfill_chats/test_gemini_cards.py \
  tests/backfill_chats/test_source_sync.py \
  tests/backfill_chats/test_freshness.py \
  tests/backfill_chats/test_scheduler.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run full backfill tests**

Run:

```bash
uv run pytest tests/backfill_chats -q
```

Expected: PASS.

- [ ] **Step 3: Run project checks**

Run:

```bash
uv run ruff check src tests
uv run pytest
```

Expected: both pass.

- [ ] **Step 4: Run a real dry-run**

Run:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity \
  --machine "$(scutil --get ComputerName)" \
  --dry-run \
  --max-sessions 5
```

Expected:
- Status is `dry_run`.
- Item count matches up to five discovered changed sessions.
- No state file is written or modified.
- Confirm `.local/source-sync-state/antigravity.json` does not exist or has the same mtime and content as before the dry-run.

- [ ] **Step 5: Run a real non-indexing sync**

Run:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity \
  --machine "$(scutil --get ComputerName)" \
  --max-sessions 5
```

Expected:
- Status is `success`.
- Cards are written.
- `.local/source-sync-state/antigravity.json` is updated.
- `index_command` is present but dry-run/skipped unless `--index` was explicitly passed.

- [ ] **Step 6: Inspect generated cards**

Run:

```bash
rg -n "backfill-agent:antigravity|source:gemini_cli_chat|User request|Assistant outcome" \
  /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli
```

Expected: generated cards contain anchors and compact sections, not raw full JSON payloads.

## Task 7: First index review

**Files:**
- No source edits.

- [ ] **Step 1: Index into a temporary review collection**

Use the real run id from Task 6:

```bash
uv run memsearch index /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli \
  -c ms_antigravity_review_<run_id>_cards_openai \
  -p openai \
  -m text-embedding-3-small
```

This path assumes `source-sync antigravity` used the default `output_root`, where the run-scoped card directory is `<memory_root>/antigravity/gemini-cli/<run_id>/cards`.

Expected: review collection indexes successfully.

- [ ] **Step 2: Run proof searches**

Search for:

```bash
rg -n "User request|backfill-agent:antigravity|source:gemini_cli_chat" \
  /Users/dominicmonkhouse/Projects/.memsearch/memory/antigravity/gemini-cli/<run_id>/cards/memory/antigravity/gemini_cli

uv run memsearch search "<known first prompt from a synced Antigravity session>" \
  -c ms_antigravity_review_<run_id>_cards_openai \
  -k 5
```

Use the literal first user prompt excerpt from the card inspected by the `rg` command as the search query. Expected: the matching Antigravity card appears in results.

- [ ] **Step 3: Decide canonical indexing**

If review passes and no secret scan findings exist, run canonical indexing explicitly:

```bash
uv run python -m memsearch.backfill.cli source-sync antigravity \
  --machine "$(scutil --get ComputerName)" \
  --index
```

Expected: canonical collection receives the card Markdown through the same source-sync path.

## Review status

- Memory recall: complete.
- Local repo discovery: complete.
- Upstream/local tool evidence: complete via installed official Gemini CLI docs and observed local files.
- Plan-document review: approved. Reviewer found no blocking issues and the three advisory clarity fixes below were folded in.
- Cross-model adversarial review: blocked. Interactive Claude CLI was attempted twice from `/Users/dominicmonkhouse/Projects/memsearch`; both normal TUI and `--ax-screen-reader` modes reached the workspace trust prompt but did not progress into the review after confirmation input. No cross-model approval should be inferred.
- Linear handoff: MON-456 — https://linear.app/monkhouseandcompany/issue/MON-456/antigravity-memsearch-capture-implementation-plan

## Plan-document review fixes

- Clarified that Gemini `lastUpdated` is stored both as `conversation.ended_at` and `metadata["last_updated"]`.
- Clarified that `antigravity-cards --input <dir>` scans direct child JSON files only; recursive discovery belongs to `source-sync antigravity`.
- Added a dry-run verification check for unchanged or absent `.local/source-sync-state/antigravity.json`.
