# Memory source freshness automation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a verified freshness layer that refreshes Manus into MemSearch weekly and Linear into MemSearch daily, without replacing the existing Markdown-first MemSearch architecture.

**Architecture:** Keep Markdown as the canonical memory source and Milvus as a rebuildable index. Add source-specific exporters for Linear and Manus, an orchestration layer that writes source cards into `.memsearch/memory/`, and dry-run scheduler definitions that can be installed only after explicit approval in an execution session.

**Tech Stack:** Python 3.11, Click CLI, pytest, Ruff, existing MemSearch backfill package, Manus API, Linear GraphQL API, Milvus/MemSearch CLI, macOS LaunchAgent templates.

---

## Linear handoff

- Linear issue: `MON-318`
- URL: https://linear.app/monkhouseandcompany/issue/MON-318/memory-source-freshness-automation-implementation-plan
- Status at plan creation: Backlog

## AP check

- Reviewer: Claude interactive CLI
- Result: CLEAN PASS
- Attempt: 2/10
- Attempt 1 changes accepted: Manus client-side diff wording, Linear `--machine`, Linear card secret scan, shared indexing wrapper, Linear 429 backoff.

## Current state

- Manus API backfill exists and is read-only.
- Existing Manus commands include `manus-estimate`, `manus-export`, `verify-manus-run`, `scan-secrets`, `manus-promote`, and `manus-cards`.
- The safe Manus recall lane is the compact card lane, not raw task logs.
- Canonical Manus cards from run `20260605-092248` are already indexed from `/Users/dominicmonkhouse/Projects/.memsearch/memory/manus-cloud/manus-api/20260605-092248/`.
- Linear is not currently a MemSearch source.
- Linear app connector auth may expire, but `LINEAR_API_KEY` bearer-token GraphQL is available and should be the automation path.
- MemSearch already has `watch`, but source APIs need scheduled polling. File watching alone does not pull new Linear or Manus data.
- The local `memsearch` repo is dirty and diverged. Executors must not touch unrelated existing changes.

## Assumptions

- First implementation target is the MacBook for code and dry-run verification.
- Always-on scheduling host is deferred. Likely final host is the Mac Mini, but that should be approved during execution after the dry-run passes.
- Linear daily sync should capture issues, comments, projects, initiatives, and documents only if available through the same authenticated API route. Start with issues and comments if documents require a separate query.
- Manus API does not support server-side `updated_at` filtering in the current client. Weekly Manus sync must be incremental by client-side diff: compare the previous state or manifest task IDs and `updated_at` values against a fresh task list, then export only tasks with changed `updated_at` values or new IDs. If no previous state exists, or if task timestamps are not reliable, the command must refuse a silent full export and require explicit `--all`.
- No canonical MemSearch indexing or LaunchAgent installation happens from this plan-writing turn.

## Not included in this version

- Graphiti/FalkorDB recall. `MON-316` covers that separately. This plan feeds MemSearch first.
- Codegraph over Linear. Codegraph is for code structure, not project/task memory.
- Obsidian vault migration. Obsidian can view Markdown later, but it is not needed for source freshness.
- Raw Manus event-log indexing. It was already rejected as noisy and slow.
- Automatic prompt-injection changes. Existing MemSearch recall behaviour stays unchanged.
- Destructive cleanup of old exports or Milvus collections.
- Installing LaunchAgents or changing Mac Mini runtime state without explicit execution approval.

## File structure

- Create `src/memsearch/backfill/linear_api.py`
  - Read-only Linear GraphQL client using `LINEAR_API_KEY`.
  - Fetches changed issues and comments since a cursor timestamp.
  - Redacts secret-like content before rendering.
- Create `src/memsearch/backfill/linear_cards.py`
  - Converts Linear entities into deterministic MemSearch card Markdown.
  - Preserves Linear identifiers, URLs, state, timestamps, labels, issue body, and comment excerpts.
- Create `src/memsearch/backfill/source_state.py`
  - Reads and writes `.local/source-sync-state/<source>.json`.
  - Stores last successful cursor, last run ID, entity counts, and failure state.
- Create `src/memsearch/backfill/source_sync.py`
  - Orchestrates daily Linear sync and weekly Manus sync.
  - Supports dry-run, lock files, and checkpointed progress.
- Create `src/memsearch/backfill/freshness.py`
  - Builds a freshness report from state files, generated cards, and MemSearch proof searches.
- Create `src/memsearch/backfill/indexing.py`
  - Shared wrapper for optional `memsearch index` calls from source sync and freshness proof flows.
  - Injectable runner for tests.
- Create `src/memsearch/backfill/scheduler.py`
  - Generates LaunchAgent plist content and wrapper commands.
  - Does not install anything by default.
- Modify `src/memsearch/backfill/cli.py`
  - Add `linear-export`, `linear-cards`, `source-sync`, `source-freshness`, and `scheduler-render`.
- Modify `docs/backfill-chat-sources.md`
  - Document Linear as a supported API source and Manus as a scheduled incremental source.
- Create `docs/source-freshness-automation.md`
  - Operator guide for daily Linear, weekly Manus, freshness reports, and scheduler installation.
- Create tests:
  - `tests/backfill_chats/test_linear_api.py`
  - `tests/backfill_chats/test_linear_cards.py`
  - `tests/backfill_chats/test_source_state.py`
  - `tests/backfill_chats/test_source_sync.py`
  - `tests/backfill_chats/test_freshness.py`
  - `tests/backfill_chats/test_scheduler.py`

## Acceptance criteria

- `uv run python -m memsearch.backfill.cli linear-export --machine "$(scutil --get ComputerName)" --since <timestamp> --output .local/linear-export/<run_id>` writes a read-only Linear export without secrets.
- `uv run python -m memsearch.backfill.cli linear-cards --machine "$(scutil --get ComputerName)" --run .local/linear-export/<run_id> --output /Users/dominicmonkhouse/Projects/.memsearch/memory/linear/<run_id>` writes deterministic card Markdown.
- Daily Linear dry-run reports changed issue/comment counts and does not duplicate already-synced entities.
- Weekly Manus dry-run reuses existing Manus commands, computes changed candidates by client-side task-list diff when prior state exists, refuses silent full export when state is missing or timestamps are unreliable, and runs `verify-manus-run`, `scan-secrets`, `manus-promote`, `scan-secrets`, `manus-cards`, and `scan-secrets`.
- Source state records last success and failure cause for both sources.
- Freshness report shows last Linear sync, last Manus sync, generated card counts, current MemSearch row count, and at least one targeted proof search per source.
- Scheduler renderer produces valid LaunchAgent plists for daily Linear and weekly Manus but does not install them.
- Normal MemSearch `index`, `search`, `expand`, and `watch` behaviour is unchanged.
- All new tests pass without live Linear or Manus credentials by using fake transports.

## Task 1: Linear API client

**Files:**
- Create: `src/memsearch/backfill/linear_api.py`
- Create: `tests/backfill_chats/test_linear_api.py`

- [ ] **Step 1: Write failing transport tests**

Create tests with a fake GraphQL transport that returns issues and comments. Assert the client sends an `Authorization` header, uses POST GraphQL, and accepts a `since` timestamp.

Run: `uv run pytest tests/backfill_chats/test_linear_api.py -q`

Expected: FAIL because `linear_api.py` does not exist.

- [ ] **Step 2: Implement the read-only client**

Implement a small client with methods:

```python
class LinearApiClient:
    def fetch_updated_issues(self, *, since: datetime | None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    def fetch_issue_comments(self, issue_id: str) -> list[dict[str, Any]]:
        ...
```

The client must:

- read `LINEAR_API_KEY` by default;
- reject missing credentials with a clear error;
- use only queries, no mutations;
- page through results;
- retry on HTTP 429 with backoff, matching the Manus client retry pattern;
- preserve raw API payloads under `.local/linear-export/`;
- avoid printing secrets.

- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/backfill_chats/test_linear_api.py -q`

Expected: PASS.

## Task 2: Linear card renderer

**Files:**
- Create: `src/memsearch/backfill/linear_cards.py`
- Create: `tests/backfill_chats/test_linear_cards.py`

- [ ] **Step 1: Write failing card-render tests**

Test that a fixture issue with two comments renders:

- one stable heading per Linear issue;
- issue identifier, title, URL, state, labels, assignee, created date, and updated date;
- body excerpt;
- comment excerpts with author and timestamp;
- no raw API token or secret-like values;
- rendered cards pass `scan_path_for_secrets` with zero hits;
- deterministic output ordering.

Run: `uv run pytest tests/backfill_chats/test_linear_cards.py -q`

Expected: FAIL because renderer does not exist.

- [ ] **Step 2: Implement card rendering**

Render cards under:

```text
/Users/dominicmonkhouse/Projects/.memsearch/memory/linear/YYYY-MM-DD/<team-key>-partN.md
```

Use headings such as:

```markdown
## Linear issue MON-123: Title
```

Each card should include:

- `Linear issue ID`
- `Linear URL`
- `State`
- `Updated`
- `Labels`
- `Project`
- `Machine`
- `Summary`
- `Recent comments`
- `Source payload`

- [ ] **Step 3: Run renderer tests**

Run: `uv run pytest tests/backfill_chats/test_linear_cards.py -q`

Expected: PASS.

## Task 3: Source sync state and locking

**Files:**
- Create: `src/memsearch/backfill/source_state.py`
- Create: `tests/backfill_chats/test_source_state.py`

- [ ] **Step 1: Write failing state tests**

Test state read/write for:

- missing state file;
- successful cursor update;
- failed run with error text;
- source lock acquisition;
- stale lock detection.

Run: `uv run pytest tests/backfill_chats/test_source_state.py -q`

Expected: FAIL because state helper does not exist.

- [ ] **Step 2: Implement state helper**

Write state under:

```text
.local/source-sync-state/linear.json
.local/source-sync-state/manus.json
```

State files are local runtime artefacts and must remain ignored by git.

- [ ] **Step 3: Run state tests**

Run: `uv run pytest tests/backfill_chats/test_source_state.py -q`

Expected: PASS.

## Task 4: Daily Linear sync command

**Files:**
- Create: `src/memsearch/backfill/source_sync.py`
- Modify: `src/memsearch/backfill/cli.py`
- Create: `tests/backfill_chats/test_source_sync.py`

- [ ] **Step 1: Write failing CLI tests**

Test:

```bash
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --dry-run
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --since 2026-06-10T00:00:00Z
```

Assert the command:

- reads state when `--since` is omitted;
- fetches updated Linear issues;
- renders cards;
- runs secret scan on output;
- reports generated file count;
- does not run `memsearch index` unless explicitly requested.
- records the running machine in state, card metadata, and manifest output.

Expected: FAIL because `source-sync` does not exist.

- [ ] **Step 2: Implement minimal daily Linear sync**

Implement `source-sync linear` with:

- `--since`
- `--machine`
- `--output-root`
- `--state-dir`
- `--dry-run`
- `--index`
- `--collection`
- `--max-issues`

Default output root:

```text
/Users/dominicmonkhouse/Projects/.memsearch/memory/linear
```

Default behaviour must be safe: export, render cards, run `scan_path_for_secrets` on rendered output, update state. Indexing is opt-in and must delegate to the shared wrapper in `src/memsearch/backfill/indexing.py`.

- [ ] **Step 3: Run Linear sync tests**

Run: `uv run pytest tests/backfill_chats/test_source_sync.py tests/backfill_chats/test_linear_api.py tests/backfill_chats/test_linear_cards.py -q`

Expected: PASS.

## Task 5: Weekly Manus sync command

**Files:**
- Modify: `src/memsearch/backfill/source_sync.py`
- Modify: `src/memsearch/backfill/cli.py`
- Modify: `tests/backfill_chats/test_source_sync.py`

- [ ] **Step 1: Write failing Manus orchestration tests**

Test `source-sync manus --dry-run` with fake Manus functions. Assert the planned sequence is:

1. estimate or fetch task list;
2. compare the fresh task list to prior state or manifest task IDs and `updated_at` values;
3. export changed tasks only when reliable client-side diff state exists;
4. refuse silent full export unless `--all` is explicitly provided;
5. verify run;
6. scan raw run;
7. promote sanitised Markdown;
8. scan promoted output;
9. generate cards;
10. scan cards;
11. update source state;
12. skip canonical indexing unless `--index` is set.

Expected: FAIL until Manus orchestration exists.

- [ ] **Step 2: Implement Manus weekly orchestration**

Reuse existing functions and CLI behaviour. Do not duplicate Manus export logic.

Add options:

- `--all`
- `--since`
- `--machine`
- `--run-id`
- `--resume`
- `--dry-run`
- `--index`
- `--collection`
- `--max-tasks`

Default output roots:

```text
.local/manus-api-export
.local/manus-api-indexable
.local/manus-api-memsearch-cards
/Users/dominicmonkhouse/Projects/.memsearch/memory/manus-cloud/manus-api
```

- [ ] **Step 3: Add changed-task guard**

If Manus API does not reliably expose updated timestamps, or if prior state is missing, the command must say so and fall back to full export only when `--all` is explicitly provided. Do not silently perform a full export from a weekly job.

- [ ] **Step 4: Run Manus sync tests**

Run: `uv run pytest tests/backfill_chats/test_source_sync.py tests/backfill_chats/test_manus_api.py tests/backfill_chats/test_cli.py -q`

Expected: PASS.

## Task 6: MemSearch indexing and proof searches

**Files:**
- Create: `src/memsearch/backfill/freshness.py`
- Create: `src/memsearch/backfill/indexing.py`
- Create: `tests/backfill_chats/test_freshness.py`

- [ ] **Step 1: Write failing freshness tests**

Test that a fake state directory and fake generated card folders produce a report with:

- source name;
- last success;
- last failure;
- generated card count;
- recommended next run;
- proof-search status.

Expected: FAIL because freshness module does not exist.

- [ ] **Step 2: Implement shared index command wrapper**

Add an internal wrapper that can run:

```bash
memsearch index <card-dir> --collection <collection> --max-chunk-size 3000
```

The wrapper must live in `src/memsearch/backfill/indexing.py`, be injectable in tests, and be disabled by default in `--dry-run`. Both `source-sync --index` and freshness proof flows must call this same wrapper.

- [ ] **Step 3: Implement proof searches**

For Linear, search for a recently synced issue identifier.

For Manus, search for a recently synced Manus task ID.

Report proof-search commands and result counts. Do not claim success from file creation alone.

- [ ] **Step 4: Run freshness tests**

Run: `uv run pytest tests/backfill_chats/test_freshness.py -q`

Expected: PASS.

## Task 7: Scheduler templates

**Files:**
- Create: `src/memsearch/backfill/scheduler.py`
- Create: `tests/backfill_chats/test_scheduler.py`
- Modify: `src/memsearch/backfill/cli.py`

- [ ] **Step 1: Write failing scheduler tests**

Test that scheduler rendering creates two plist definitions:

- `com.memsearch.daily-linear-sync`
- `com.memsearch.weekly-manus-sync`

Assert:

- daily Linear runs at 06:30 local time;
- weekly Manus runs Monday at 06:00 local time;
- commands use absolute repo paths;
- output logs go under `.local/source-sync-logs/`;
- rendered plists are not installed automatically.

Expected: FAIL because scheduler renderer does not exist.

- [ ] **Step 2: Implement renderer**

Add:

```bash
uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents
```

The command writes plist files and a dry-run summary only.

- [ ] **Step 3: Add install instructions to docs only**

Document the exact future install commands, but mark them as approval-gated. The implementation must not run `launchctl` during normal tests or plan execution.

- [ ] **Step 4: Run scheduler tests**

Run: `uv run pytest tests/backfill_chats/test_scheduler.py -q`

Expected: PASS.

## Task 8: Documentation and operator guide

**Files:**
- Modify: `docs/backfill-chat-sources.md`
- Create: `docs/source-freshness-automation.md`

- [ ] **Step 1: Document source policy**

Update `docs/backfill-chat-sources.md` with:

- Linear route;
- weekly Manus route;
- daily versus weekly rationale;
- source state locations;
- secret scan gates;
- indexing gates;
- no raw Manus indexing.

- [ ] **Step 2: Write operator guide**

Create `docs/source-freshness-automation.md` with:

- one-off dry-run commands;
- daily Linear command;
- weekly Manus command;
- freshness report command;
- scheduler render command;
- approval gates before installing LaunchAgents;
- recovery steps for failed syncs.

- [ ] **Step 3: Run documentation check**

Run:

```bash
uv run ruff check src/memsearch/backfill tests/backfill_chats
uv run pytest tests/backfill_chats -q
```

Expected: PASS.

## Task 9: End-to-end dry run

**Files:**
- No new files unless tests expose a missing fixture.

- [ ] **Step 1: Run Linear dry run**

Run:

```bash
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --dry-run --max-issues 5
```

Expected:

- no canonical indexing;
- no LaunchAgent installation;
- exported issue count reported;
- rendered card paths reported;
- state update preview reported.

- [ ] **Step 2: Run Manus dry run**

Run:

```bash
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)" --dry-run --max-tasks 5
```

Expected:

- no full export unless explicitly requested;
- no canonical indexing;
- orchestration sequence reported;
- state update preview reported.

- [ ] **Step 3: Run freshness report**

Run:

```bash
uv run python -m memsearch.backfill.cli source-freshness
```

Expected:

- Linear and Manus show last success or clear missing-state message;
- report includes next scheduled run recommendation;
- proof-search section is present.

## Task 10: Linear handoff and execution control

**Files:**
- No code files.

- [ ] **Step 1: Update owning Linear issue**

Create or update the Linear issue with:

- absolute plan path;
- goal line;
- no deployment statement;
- expected execution order;
- current repo dirty/diverged warning.

- [ ] **Step 2: Add execution note**

The execution agent must load the Linear issue first, verify it references this exact plan path, and write progress back to Linear after each task.

- [ ] **Step 3: Stop for approval**

Do not implement this plan until Dom explicitly says `go`, `do it`, `implement`, or equivalent after reviewing the plan.

## Verification gate for implementation

Run before claiming implementation complete:

```bash
uv run pytest tests/backfill_chats -q
uv run ruff check src/memsearch/backfill tests/backfill_chats
uv run python -m memsearch.backfill.cli source-sync linear --machine "$(scutil --get ComputerName)" --dry-run --max-issues 5
uv run python -m memsearch.backfill.cli source-sync manus --machine "$(scutil --get ComputerName)" --dry-run --max-tasks 5
uv run python -m memsearch.backfill.cli scheduler-render --output .local/launchagents
uv run python -m memsearch.backfill.cli source-freshness
```

Implementation is not complete until the running commands prove the code path works. Editing docs or config alone is not enough.
