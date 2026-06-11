# Graphiti FalkorDB Memory Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a verified Graphiti + FalkorDB pilot to MemSearch as an optional derived knowledge-graph recall layer without replacing Markdown, Milvus, or existing memory-recall behaviour.

**Architecture:** Keep MemSearch's current contract: Markdown is canonical and Milvus is the rebuildable semantic/BM25 index. Add Graphiti as a sidecar derived index fed from the same Markdown memory files, with FalkorDB as Graphiti's default graph backend. The first version exposes explicit CLI commands for graph indexing and graph search only; no automatic prompt injection changes until the pilot proves useful and stable.

**Tech Stack:** Python 3.10+, existing MemSearch CLI/config/test stack, Graphiti MCP server, FalkorDB, HTTP MCP endpoint, pytest, ruff, `uv run python -m pytest`, optional Docker/Docker Compose or equivalent container runtime.

---

## Evidence Checked

- Local MemSearch architecture:
  - `README.md`: MemSearch positions Markdown as the source of truth and Milvus as a shadow index.
  - `docs/architecture.md`: indexing flow, chunk metadata, progressive disclosure, per-project collection isolation.
  - `docs/design-philosophy.md`: Markdown-first design, hybrid search, Milvus rationale.
  - `src/memsearch/core.py`: Markdown scan -> chunk -> embed -> store flow.
  - `src/memsearch/store.py`: Milvus schema and hybrid dense + BM25 search.
  - `src/memsearch/config.py`: layered config model.
  - `src/memsearch/cli.py`: command layout for `index`, `search`, and `expand`.
  - `plugins/codex/hooks/session-start.sh` and `plugins/codex/hooks/user-prompt-submit.sh`: current hook injection path.
- Upstream Graphiti/FalkorDB evidence:
  - Graphiti MCP README documents a temporal knowledge-graph MCP server with episode management, entity/fact search, `group_id` isolation, HTTP endpoint at `/mcp/`, and database support for FalkorDB as default plus Neo4j.
  - Graphiti MCP README documents Docker Compose as the default FalkorDB + MCP server route.
  - FalkorDB docs position Graphiti as temporally-aware agent memory and recommend the Graphiti MCP server for persistent Claude/Cursor-style memory.
  - Graphiti issues show live backend churn: Kuzu archive concern, Kuzu add-episode crash, FalkorDB `group_id` validation issues, Neo4j backend issues. This argues for a contained pilot with rollback, not a default-on integration.
  - Kuzu docs and repo confirm Kuzu is embedded/in-process, but the repo states KuzuDB is archived and previous releases remain usable. That makes Kuzu a deferred local experiment rather than the first MemSearch graph backend.

## Current State

- The local project repo is `/Users/dominicmonkhouse/Projects/memsearch`.
- The repo is currently dirty and diverged:
  - `main...origin/main [ahead 1, behind 1]`
  - Modified: `plugins/claude-code/skills/memory-recall/SKILL.md`
  - Modified: `plugins/codex/skills/memory-recall/SKILL.md`
  - Untracked: `.local/`
  - Untracked: `docs/superpowers/`
- Local Docker, Podman, and Colima were not found on PATH while writing this plan.
- Port `8000` is already occupied by a local Python process, so the default Graphiti HTTP port cannot be assumed free.
- Port `6379` was free during plan writing.
- Tasks 1-2 are shippable without a running Graphiti server. Tasks 3-8 are runtime-dependent and must stop cleanly if no local/Mac Mini Graphiti runtime can be verified.

## Non-Negotiable Design Rules

- Markdown remains canonical. The graph is always rebuildable from Markdown and never becomes the source of truth.
- Milvus remains the primary automatic recall path. Graphiti is an explicit second-stage recall path until proven.
- Do not modify Claude/Codex prompt injection in this version.
- Do not delete or rewrite existing memory files.
- Do not add Kuzu support in this version. Record the decision trail and revisit only after a FalkorDB pilot.
- No secrets in repo files. Use `env:OPENAI_API_KEY` style references or local `.env` files that are ignored by git.
- All networked Graphiti/FalkorDB tests must be opt-in and skipped by default in normal unit test runs.

## Files and Responsibilities

- Create: `src/memsearch/graphiti/__init__.py`
  - Package marker for optional Graphiti integration.
- Create: `src/memsearch/graphiti/episodes.py`
  - Converts Markdown memory sections into deterministic Graphiti episodes with provenance metadata.
- Create: `src/memsearch/graphiti/client.py`
  - Thin Graphiti MCP client for tools: `get_status`, `add_memory`, `search_memory_facts`, `search_nodes`, `get_episode_entities`.
  - Must use an official MCP client library or a protocol probe verified against a live Graphiti MCP server. Do not assume a plain JSON-RPC POST shape until tested.
  - The public adapter shape is allowed to become async or context-managed if the proven MCP transport requires it.
- Create: `src/memsearch/graphiti/sync.py`
  - Incremental sync logic from Markdown source files to Graphiti episodes, including a local manifest.
- Create: `src/memsearch/graphiti/search.py`
  - Explicit graph recall helpers that combine Graphiti fact/node hits with MemSearch source provenance.
- Create: `src/memsearch/graphiti/manifest.py`
  - Reads/writes `.memsearch/graphiti-manifest.json` with source path, section lines, content hash, episode UUID, status, and last error.
- Modify: `src/memsearch/config.py`
  - Add optional `GraphitiConfig` under `MemSearchConfig`.
- Modify: `src/memsearch/cli.py`
  - Add `graph-status`, `graph-index`, and `graph-search` commands.
- Modify: `pyproject.toml`
  - Add optional dependency group `graphiti` only if the official MCP client or direct Graphiti libraries are required. Prefer the smallest maintained dependency that proves compatibility with Graphiti MCP.
- Create: `tests/test_graphiti_config.py`
  - Config defaults and override parsing.
- Create: `tests/test_graphiti_episodes.py`
  - Markdown-to-episode extraction and provenance tests.
- Create: `tests/test_graphiti_manifest.py`
  - Idempotent manifest updates and stale/error states.
- Create: `tests/test_graphiti_sync.py`
  - Sync orchestration tests for batch limits, retry/error handling, client calls, and manifest writes.
- Create: `tests/test_graphiti_client.py`
  - Mocked client-boundary tests for the proven Graphiti MCP route.
- Create: `tests/test_graphiti_cli.py`
  - CLI command tests with fake client, no real server.
- Create: `docs/graphiti-falkordb.md`
  - Operator guide for starting Graphiti/FalkorDB, configuring MemSearch, indexing graph memory, searching graph memory, and rolling back.
- Create: `docs/graphiti-falkordb-pilot-results.md`
  - Pilot evidence log with exact commands, fixture counts, search probes, failures, and keep/remove decision.
- Create: `.gitignore` entry if needed:
  - `.local/`
  - Graphiti `.env` files or generated database files.
  - Do not add `.memsearch/graphiti-manifest.json` because `.gitignore` already ignores `.memsearch/`.

## Not Included In This Version

- **Kuzu backend:** considered because it is embedded and closer to MemSearch's local-first style. Not included because KuzuDB is archived and current Graphiti issue traffic includes Kuzu backend crashes/timezone concerns. Revisit only if the FalkorDB pilot proves graph recall is valuable and a maintained embedded backend becomes attractive.
- **Neo4j backend:** considered because Graphiti supports it and Neo4j has a mature GraphRAG ecosystem. Not included because it adds more operational weight than FalkorDB for the first pilot.
- **Automatic Claude/Codex prompt injection:** not included because Graphiti recall could add cost and noise. First version is explicit CLI recall only.
- **Replacing Milvus:** not included. Milvus remains the dense + BM25 retrieval layer.
- **Production SaaS hosting:** not included. This is local or Mac Mini sidecar first.
- **Bulk backfill of every historical transcript on day one:** not included. Start with a small manifest-driven pilot.

## Open Decisions

- **Runtime host:** MacBook local pilot versus Mac Mini always-on service. Proposed default: MacBook pilot first because the active MemSearch repo and current session are on the MacBook. Move to Mac Mini only after the local pilot passes.
- **Container runtime:** Docker is not on PATH locally. Executor must either install/enable Docker Desktop/Colima with approval, or run Graphiti MCP standalone against an external FalkorDB instance. Do not assume `docker compose up` works.
- **HTTP port:** Graphiti default `8000` is occupied locally. Proposed default: use `8018` for the pilot.
- **Graph group_id naming:** Proposed default: reuse MemSearch's derived project collection slug, for example `ms_memsearch_ae2d4f9b`, normalised to Graphiti's allowed `group_id` characters.
- **Episode granularity:** Proposed default: one episode per Markdown memory section, not one episode per full file. This preserves provenance and keeps extraction payloads small.

## Acceptance Criteria

- `memsearch graph-status` returns Graphiti server status and fails clearly when the server is not reachable.
- `memsearch graph-index <memory-dir> --limit 10` adds exactly 10 deterministic episodes to Graphiti and writes a manifest.
- Re-running the same `graph-index` command adds zero duplicate episodes.
- `memsearch graph-search "what changed about Kuzu"` returns Graphiti facts/nodes with source file and line provenance.
- Normal MemSearch `index`, `search`, and `expand` behaviours are unchanged.
- Default unit tests pass without a running Graphiti server.
- Optional live smoke test proves Graphiti/FalkorDB can start, accept episodes, and return facts.
- Graphiti client implementation uses a protocol route proven against a live Graphiti MCP server, not a guessed raw HTTP shape.
- Pilot evidence says keep, change, or remove the integration.

## Task 1: Graphiti Config

**Files:**
- Modify: `src/memsearch/config.py`
- Create: `tests/test_graphiti_config.py`

- [ ] **Step 1: Write failing config tests**

```python
def test_graphiti_config_defaults_disabled():
    from memsearch.config import MemSearchConfig

    cfg = MemSearchConfig()

    assert cfg.graphiti.enabled is False
    assert cfg.graphiti.endpoint == "http://127.0.0.1:8018/mcp/"
    assert cfg.graphiti.group_id == ""
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run python -m pytest tests/test_graphiti_config.py -v
```

Expected: FAIL because `MemSearchConfig.graphiti` does not exist.

- [ ] **Step 3: Add `GraphitiConfig`**

Add:

```python
@dataclass
class GraphitiConfig:
    enabled: bool = False
    transport: str = "mcp-streamable-http"
    endpoint: str = "http://127.0.0.1:8018/mcp/"
    group_id: str = ""
    batch_size: int = 10
    request_timeout_seconds: int = 120
    manifest_path: str = ".memsearch/graphiti-manifest.json"
```

Add `graphiti: GraphitiConfig = field(default_factory=GraphitiConfig)` to `MemSearchConfig` and add `"graphiti": GraphitiConfig` to `_SECTION_CLASSES`.
Add `request_timeout_seconds` to `_INT_FIELDS` so `memsearch config set graphiti.request_timeout_seconds 60` persists an integer, not a string.
Add config tests proving `memsearch config set graphiti.enabled true`, `graphiti.endpoint`, `graphiti.transport`, and `graphiti.request_timeout_seconds` work through the existing generic two-part config path. Do not update the interactive `config init` wizard in this version unless the executor deliberately decides graphiti should appear in first-run setup.

- [ ] **Step 4: Run the test**

Run:

```bash
uv run python -m pytest tests/test_graphiti_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full local gate**

Run:

```bash
uv run python -m pytest tests/test_config.py tests/test_cli_config_helpers.py tests/test_graphiti_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/memsearch/config.py tests/test_graphiti_config.py
git commit -m "feat: add graphiti config"
```

## Task 2: Markdown Episodes

**Files:**
- Create: `src/memsearch/graphiti/__init__.py`
- Create: `src/memsearch/graphiti/episodes.py`
- Create: `tests/test_graphiti_episodes.py`

- [ ] **Step 1: Write failing episode extraction tests**

```python
def test_sections_become_deterministic_episodes(tmp_path):
    memory = tmp_path / "2026-06-11.md"
    memory.write_text(
        "## Session 10:00\n\n"
        "### 10:01\n"
        "<!-- session:abc rollout:/tmp/session.jsonl -->\n"
        "- User asked about Kuzu.\n"
        "- Assistant recommended Graphiti plus FalkorDB.\n",
        encoding="utf-8",
    )

    from memsearch.graphiti.episodes import build_episodes

    episodes = list(build_episodes([memory]))

    assert len(episodes) == 1
    assert episodes[0].name.startswith("2026-06-11.md:10:01")
    assert "Graphiti plus FalkorDB" in episodes[0].body
    assert episodes[0].metadata["source"] == str(memory)
    assert episodes[0].metadata["start_line"] > 0
    assert episodes[0].content_hash
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run python -m pytest tests/test_graphiti_episodes.py -v
```

Expected: FAIL because `memsearch.graphiti.episodes` does not exist.

- [ ] **Step 3: Implement minimal episode builder**

Implement a dataclass:

```python
@dataclass(frozen=True)
class GraphitiEpisode:
    name: str
    body: str
    source_description: str
    reference_time: str | None
    metadata: dict[str, Any]
    content_hash: str
```

Use heading-based section parsing consistent with `chunker.py`. Keep HTML comments in episode body for provenance, but include a cleaned `source_description` such as `memsearch markdown memory`.

- [ ] **Step 4: Run episode tests**

Run:

```bash
uv run python -m pytest tests/test_graphiti_episodes.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full local gate for touched area**

Run:

```bash
uv run python -m pytest tests/test_chunker.py tests/test_graphiti_episodes.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/memsearch/graphiti/__init__.py src/memsearch/graphiti/episodes.py tests/test_graphiti_episodes.py
git commit -m "feat: build graphiti episodes from markdown memory"
```

## Task 3: Local Graphiti Runtime Preflight

**Files:**
- Create: `docs/graphiti-falkordb.md`
- Create: `docs/graphiti-falkordb-pilot-results.md`

- [ ] **Step 1: Verify container/runtime availability**

Run:

```bash
command -v docker || true
docker --version 2>/dev/null || true
command -v colima || true
command -v podman || true
```

Expected: at least one viable container/runtime route exists. If none exists, stop and record `blocked: no container runtime found` in `docs/graphiti-falkordb-pilot-results.md`. Do not install Docker, Colima, or Podman without explicit approval.

- [ ] **Step 2: Verify LLM/embedder credentials without printing secrets**

Run:

```bash
set -a
[ -f "$HOME/.secrets/mcp.env" ] && source "$HOME/.secrets/mcp.env"
set +a
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY available" || echo "OPENAI_API_KEY missing"
```

Expected: an API key or configured local provider required by Graphiti is available. If absent, stop and record `blocked: missing Graphiti LLM/embedder credentials`. Do not print key values.

- [ ] **Step 3: Verify ports**

Run:

```bash
lsof -nP -iTCP:8018 -sTCP:LISTEN || true
lsof -nP -iTCP:6379 -sTCP:LISTEN || true
```

Expected: no listener on `8018`. `6379` may be free or occupied by an intentional local Redis. If `6379` is occupied, choose a non-conflicting FalkorDB host port and document it.

- [ ] **Step 4: Clone or update Graphiti outside MemSearch**

Run:

```bash
cd /Users/dominicmonkhouse/Projects
test -d graphiti/.git || git clone https://github.com/getzep/graphiti.git graphiti
git -C graphiti fetch --all --prune
git -C graphiti status --short --branch
```

Expected: Graphiti exists in `/Users/dominicmonkhouse/Projects/graphiti`. Do not vendor Graphiti into MemSearch.

- [ ] **Step 5: Create a local ignored Graphiti runtime config**

Read Graphiti's current `mcp_server` compose/config files and identify the documented way to set the HTTP MCP host port. Create only local ignored runtime config in the Graphiti checkout or under MemSearch `.local/graphiti/`.

Required result:
- Graphiti MCP listens on `127.0.0.1:8018`, not `8000`;
- FalkorDB uses a non-conflicting host port;
- `.env` or config files containing secrets are ignored by git;
- the exact config path is written into `docs/graphiti-falkordb.md`.

Do not proceed with Task 4 until this is proven.

- [ ] **Step 6: Start Graphiti MCP + FalkorDB**

Use Graphiti's documented route after applying the local port/config override:

```bash
cd /Users/dominicmonkhouse/Projects/graphiti/mcp_server
docker compose up
```

If the selected runtime is not Docker, replace this with the verified equivalent and document it before running. Do not leave a long-running foreground process in the executor session; use a managed background session or a separate terminal.

- [ ] **Step 7: Verify health**

Run:

```bash
curl -fsS http://127.0.0.1:8018/health
```

Expected: health endpoint succeeds. Record the command output in `docs/graphiti-falkordb-pilot-results.md`.

- [ ] **Step 8: Commit preflight docs**

```bash
git add docs/graphiti-falkordb.md docs/graphiti-falkordb-pilot-results.md
git commit -m "docs: record graphiti falkordb runtime preflight"
```

## Task 4: Graphiti MCP Protocol Probe

**Files:**
- Create: `src/memsearch/graphiti/client.py`
- Create: `tests/test_graphiti_client.py`
- Modify: `pyproject.toml` if an official MCP client dependency is needed

- [ ] **Step 1: Verify the client protocol before coding**

Start from Graphiti's documented HTTP MCP endpoint, but do not assume the wire format. First prove one of these works against a live Graphiti MCP server:

- official Python MCP client with streamable HTTP transport;
- official MCP remote/gateway route;
- direct Graphiti Python API against FalkorDB.

Record the chosen route in `docs/graphiti-falkordb.md`. If no route can be proven, stop this task and update `docs/graphiti-falkordb-pilot-results.md` with the blocker. Do not implement a guessed client.
Also verify that Graphiti fact/node search results include the originating episode UUID or an equivalent provenance key that can be joined back to the manifest. If no round-trip provenance key is returned, record this as a provenance blocker in `docs/graphiti-falkordb-pilot-results.md` and degrade `graph-search` output to omit source file and line data until a proven round-trip mechanism exists.

- [ ] **Step 2: Write failing mocked client tests for the proven route**

If using an official MCP client, monkeypatch the client boundary rather than mocking raw HTTP details. The test should prove MemSearch calls the Graphiti tool names and passes `group_id`, episode body, and provenance.

Example test shape:

```python
def test_add_memory_calls_graphiti_tool(monkeypatch):
    calls = []

    class FakeTransport:
        def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return {"episode_uuid": "episode-1"}

    from memsearch.graphiti.client import GraphitiClient
    from memsearch.graphiti.episodes import GraphitiEpisode

    client = GraphitiClient("http://127.0.0.1:8018/mcp/", transport=FakeTransport())
    episode = GraphitiEpisode(
        name="memory.md:3",
        body="Graphiti plus FalkorDB",
        source_description="memsearch markdown memory",
        reference_time=None,
        metadata={"source": "/tmp/memory.md", "start_line": 3, "end_line": 7},
        content_hash="abc",
    )

    result = client.add_memory(episode, group_id="ms_memsearch_ae2d4f9b")

    assert result["episode_uuid"] == "episode-1"
    assert calls[0][0] == "add_memory"
    assert calls[0][1]["group_id"] == "ms_memsearch_ae2d4f9b"
```

- [ ] **Step 3: Run the failing test**

Run:

```bash
uv run python -m pytest tests/test_graphiti_client.py -v
```

Expected: FAIL because the client does not exist.

- [ ] **Step 4: Implement the minimal client adapter**

Implement a small adapter over the proven client route:

```python
class GraphitiClient:
    def __init__(self, endpoint: str, timeout: int = 30) -> None: ...
    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def get_status(self) -> dict[str, Any]: ...
    def add_memory(self, episode: GraphitiEpisode, *, group_id: str) -> dict[str, Any]: ...
    def search_memory_facts(self, query: str, *, group_id: str, limit: int = 10) -> dict[str, Any]: ...
    def search_nodes(self, query: str, *, group_id: str, limit: int = 10) -> dict[str, Any]: ...
```

Keep payload construction covered by tests because Graphiti MCP tool names are the contract. If adding a dependency is necessary, add it under `memsearch[graphiti]` and keep normal installs unchanged.

- [ ] **Step 5: Run mocked client tests**

Run:

```bash
uv run python -m pytest tests/test_graphiti_client.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full local gate for touched area**

Run:

```bash
uv run python -m pytest tests/test_graphiti_client.py tests/test_graphiti_episodes.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/memsearch/graphiti/client.py tests/test_graphiti_client.py
git diff --quiet -- pyproject.toml || git add pyproject.toml
git commit -m "feat: add graphiti mcp client"
```

## Task 5: Incremental Graph Sync Manifest

**Files:**
- Create: `src/memsearch/graphiti/manifest.py`
- Create: `src/memsearch/graphiti/sync.py`
- Create: `tests/test_graphiti_manifest.py`
- Create: `tests/test_graphiti_sync.py`

- [ ] **Step 1: Write failing idempotency tests**

```python
def test_manifest_skips_synced_content_hash(tmp_path):
    from memsearch.graphiti.manifest import GraphitiManifest

    path = tmp_path / "manifest.json"
    manifest = GraphitiManifest(path)
    manifest.mark_synced(
        source="/tmp/memory.md",
        start_line=3,
        end_line=7,
        content_hash="abc",
        episode_uuid="episode-1",
    )
    manifest.save()

    reloaded = GraphitiManifest(path)

    assert reloaded.is_synced("/tmp/memory.md", 3, 7, "abc")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run python -m pytest tests/test_graphiti_manifest.py -v
```

Expected: FAIL because manifest code does not exist.

- [ ] **Step 3: Implement manifest and sync orchestration**

Manifest record shape:

```json
{
  "source": "/abs/path/2026-06-11.md",
  "start_line": 10,
  "end_line": 15,
  "content_hash": "16hex",
  "episode_uuid": "graphiti-uuid",
  "synced_at": "2026-06-11T12:00:00Z",
  "status": "synced",
  "last_error": ""
}
```

Sync rules:
- skip existing `(source, start_line, end_line, content_hash)` records with `status == "synced"`;
- retry records with `status == "error"`;
- write manifest atomically via temp file then rename;
- acquire a simple lock file beside the manifest before reading/writing to prevent two `graph-index` runs from syncing the same episode concurrently;
- save progress after every successfully synced episode so a long LLM-backed batch can resume after timeout/rate-limit failures;
- never prune Graphiti in this version unless an explicit `--rebuild` flag is added later.

- [ ] **Step 4: Write sync orchestration tests**

Add tests that prove:
- `--limit 10` stops after 10 client calls when more than 10 episodes exist;
- already-synced manifest records are skipped;
- error records are retried;
- a client exception marks that episode as `error` and preserves prior successes;
- a second run cannot acquire the lock while the first lock is active.

- [ ] **Step 5: Run manifest and sync tests**

Run:

```bash
uv run python -m pytest tests/test_graphiti_manifest.py tests/test_graphiti_sync.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full local gate for touched area**

Run:

```bash
uv run python -m pytest tests/test_graphiti_manifest.py tests/test_graphiti_sync.py tests/test_graphiti_episodes.py tests/test_graphiti_client.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/memsearch/graphiti/manifest.py src/memsearch/graphiti/sync.py tests/test_graphiti_manifest.py tests/test_graphiti_sync.py
git commit -m "feat: sync markdown memory to graphiti"
```

## Task 6: CLI Commands

**Files:**
- Modify: `src/memsearch/cli.py`
- Create: `src/memsearch/graphiti/search.py`
- Create: `tests/test_graphiti_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
from click.testing import CliRunner


def test_graph_status_command_exists():
    from memsearch.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["graph-status"])

    assert result.exit_code != 2
```

Also add tests that monkeypatch `GraphitiClient` so no real Graphiti server is needed:
- `graph-status` calls `get_status()` and prints the returned status;
- `graph-index --limit 10` passes the limit into the sync runner;
- `graph-search` prints source path and line range from returned provenance;
- unavailable Graphiti returns a clear non-zero error.

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run python -m pytest tests/test_graphiti_cli.py -v
```

Expected: FAIL because commands do not exist.

- [ ] **Step 3: Add `graph-status`**

Command:

```bash
memsearch graph-status --endpoint http://127.0.0.1:8018/mcp/
```

Expected output when available: status text from Graphiti MCP.

Expected output when unavailable: clear non-zero error naming endpoint and timeout.

- [ ] **Step 4: Add `graph-index`**

Command:

```bash
memsearch graph-index <memory-dir> --limit 10 --group-id ms_memsearch_ae2d4f9b
```

Options:
- `--limit`: pilot cap, default 10;
- `--group-id`: required unless config supplies it;
- `--manifest`: defaults to config path;

- [ ] **Step 5: Add `graph-search`**

Command:

```bash
memsearch graph-search "what changed about Kuzu" --group-id ms_memsearch_ae2d4f9b --top-k 5
```

Output must include:
- fact or node summary;
- score if Graphiti returns one;
- source file;
- line range if available;
- episode UUID if available.

- [ ] **Step 6: Run CLI tests**

Run:

```bash
uv run python -m pytest tests/test_graphiti_cli.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full local gate for touched area**

Run:

```bash
uv run python -m pytest tests/test_graphiti_config.py tests/test_graphiti_episodes.py tests/test_graphiti_client.py tests/test_graphiti_manifest.py tests/test_graphiti_sync.py tests/test_graphiti_cli.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/memsearch/cli.py src/memsearch/graphiti/search.py tests/test_graphiti_cli.py
git commit -m "feat: add graphiti cli commands"
```

## Task 7: Local Runtime Guide

**Files:**
- Modify: `docs/graphiti-falkordb.md`
- Modify: `.gitignore`

- [ ] **Step 1: Write the operator guide**

Include:
- upstream links checked;
- current local caveat: Docker was not found on PATH during plan writing;
- current local caveat: port `8000` was occupied, so pilot uses `8018`;
- how to clone Graphiti outside the MemSearch repo, for example `/Users/dominicmonkhouse/Projects/graphiti`;
- how to run Graphiti MCP with FalkorDB using Graphiti's documented Docker Compose route when Docker is available;
- how to configure Graphiti HTTP port to `8018`;
- how to configure MemSearch `[graphiti]`;
- how to run `graph-status`, `graph-index`, and `graph-search`;
- how to stop/remove the Graphiti runtime without deleting Markdown or Milvus data.

- [ ] **Step 2: Add ignored local runtime paths**

Add only if absent:

```gitignore
.local/
```

Before editing `.gitignore`, read the full file and confirm the line is not already present. Do not add `.memsearch/graphiti-manifest.json`; `.gitignore` already ignores `.memsearch/`. Use `.local/` rather than only `.local/graphiti/` because `.local/` already exists as an untracked local runtime artefact.

- [ ] **Step 3: Re-read `.gitignore` and the guide**

Run:

```bash
sed -n '1,220p' .gitignore
sed -n '1,260p' docs/graphiti-falkordb.md
```

Expected: guide is complete and ignored paths are present exactly once.

- [ ] **Step 4: Commit**

```bash
git add docs/graphiti-falkordb.md .gitignore
git commit -m "docs: add graphiti falkordb runtime guide"
```

## Task 8: Optional Live Smoke Test

**Files:**
- Modify: `docs/graphiti-falkordb-pilot-results.md`

- [ ] **Step 1: Confirm Task 3 preflight is still valid**

Re-run the Task 3 runtime, credential, and port checks. If anything changed, update `docs/graphiti-falkordb-pilot-results.md` before proceeding.

- [ ] **Step 2: Resolve and verify the pilot memory directory**

Derive the memory directory from the active MemSearch project before indexing. Do not hardcode a path that has not been checked.

Run:

```bash
if [ -n "${MEMSEARCH_DIR:-}" ]; then
  MEMORY_ROOT="$MEMSEARCH_DIR/memory"
elif [ -d "/Users/dominicmonkhouse/Projects/memsearch/.memsearch/memory" ]; then
  MEMORY_ROOT="/Users/dominicmonkhouse/Projects/memsearch/.memsearch/memory"
elif [ -d "/Users/dominicmonkhouse/Projects/.memsearch/memory" ]; then
  MEMORY_ROOT="/Users/dominicmonkhouse/Projects/.memsearch/memory"
else
  echo "NO_MEMORY_ROOT"
fi
test -d "$MEMORY_ROOT"
find "$MEMORY_ROOT" -maxdepth 1 -type f -name '*.md' | head
```

Expected: `MEMORY_ROOT` exists and contains markdown files. Record the exact resolved path in `docs/graphiti-falkordb-pilot-results.md`.

- [ ] **Step 3: Verify ports**

Run:

```bash
lsof -nP -iTCP:8018 -sTCP:LISTEN || true
lsof -nP -iTCP:6379 -sTCP:LISTEN || true
```

Expected: no listener on `8018`; `6379` may be free or may be occupied by an intentional local Redis. If `6379` is occupied, use a compose override/local config to map FalkorDB to a different host port and document the exact override path.

- [ ] **Step 4: Start Graphiti MCP + FalkorDB using the verified config**

Use the route and config path recorded in `docs/graphiti-falkordb.md`:

```bash
cd /Users/dominicmonkhouse/Projects/graphiti/mcp_server
docker compose up
```

If the selected runtime is not Docker, use the verified equivalent from Task 3. Do not commit vendored Graphiti compose files into MemSearch.

- [ ] **Step 5: Check health**

Run:

```bash
curl -fsS http://127.0.0.1:8018/health
memsearch graph-status --endpoint http://127.0.0.1:8018/mcp/
```

Expected: both succeed.

- [ ] **Step 6: Index a 10-episode pilot**

Run:

```bash
memsearch graph-index "$MEMORY_ROOT" --limit 10 --group-id ms_memsearch_ae2d4f9b --endpoint http://127.0.0.1:8018/mcp/
```

Expected: 10 synced, manifest written, no duplicate errors.

- [ ] **Step 7: Prove idempotency**

Run the same command again.

Expected: 0 new synced, 10 skipped.

- [ ] **Step 8: Probe graph recall**

Run:

```bash
memsearch graph-search "what changed about Kuzu and Graphiti?" --group-id ms_memsearch_ae2d4f9b --endpoint http://127.0.0.1:8018/mcp/ --top-k 5
```

Expected: results include source provenance back to Markdown memory sections.

- [ ] **Step 9: Record results**

Write `docs/graphiti-falkordb-pilot-results.md` with:
- exact date/time;
- Graphiti commit/version if available;
- FalkorDB image/version if available;
- commands run;
- counts synced/skipped/errored;
- search output excerpt;
- keep/change/remove recommendation.

- [ ] **Step 10: Commit pilot results**

```bash
git add docs/graphiti-falkordb-pilot-results.md
git commit -m "docs: record graphiti falkordb pilot results"
```

## Task 9: Full Verification

**Files:**
- All files touched in Tasks 1-8.

- [ ] **Step 1: Run unit tests**

```bash
uv run python -m pytest tests/test_graphiti_config.py tests/test_graphiti_episodes.py tests/test_graphiti_client.py tests/test_graphiti_manifest.py tests/test_graphiti_sync.py tests/test_graphiti_cli.py -v
```

Expected: PASS.

- [ ] **Step 2: Run project test gate**

```bash
uv run python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Run lint**

```bash
uv run ruff check src tests
```

Expected: PASS.

- [ ] **Step 4: Verify existing MemSearch behaviour**

Run:

```bash
memsearch --help
memsearch search "memsearch graphiti falkordb" --top-k 3 --json-output
```

Expected: existing commands still work. Search may return no relevant result depending on current indexed memory, but it must not fail because Graphiti is absent.

- [ ] **Step 5: Verify no automatic hook behaviour changed**

Run:

```bash
git diff -- plugins/claude-code/hooks plugins/codex/hooks
```

Expected: no hook changes in this plan unless a later approved plan explicitly adds graph recall to prompt injection.

- [ ] **Step 6: Final commit if needed**

```bash
git status --short
```

Expected: only intentional files remain staged/committed. Do not touch unrelated pre-existing modified files.

## Risks and Mitigations

- **Graphiti backend churn:** Keep Graphiti explicit, optional, and derived. Do not wire into automatic prompts in this version.
- **Kuzu temptation:** Kuzu is a better local-first shape, but current upstream support risk is too high for the first stack change. Defer.
- **Docker unavailable:** Make runtime setup a documented blocker. Do not fabricate a working compose path if local runtime is absent.
- **Port conflict:** Use `8018` in MemSearch docs/config examples instead of Graphiti's default `8000`.
- **LLM extraction cost:** Pilot with `--limit 10` first. Do not backfill all memory until cost and latency are measured.
- **LLM extraction timeout/rate limits:** Save manifest progress after every episode, use a 120-second default request timeout, and retry error records explicitly rather than rerunning the whole batch blindly.
- **Provenance loss:** Every episode must carry source path, line range, heading, and content hash.
- **Duplication:** Manifest idempotency is required before any bulk indexing.
- **Pinned upstream risk:** Record the Graphiti commit/tag used by the pilot in `docs/graphiti-falkordb-pilot-results.md`; do not build against an unrecorded moving HEAD.

## Review Status

- Plan written from local MemSearch source plus current upstream Graphiti/FalkorDB/Kuzu evidence.
- Plan-document review: approved after fixes to runtime order, credentials, port override, config/file contradictions, CLI fixture pattern, and `.gitignore` guidance.
- Cross-model adversarial review: completed via interactive Claude CLI. Fixes folded in: sync tests, protocol-flexible client wording, shippable boundary when no runtime exists, pilot memory-root verification, per-episode progress, lock-file duplicate prevention, and upstream commit recording.
- AP check attempt 1: accepted and folded in fixes for `request_timeout_seconds` integer config handling, broader `.local/` ignore guidance, Task 6 sync test coverage, Graphiti search provenance round-trip proof, and conditional `pyproject.toml` staging.
- AP check attempt 2: CLEAN PASS from Claude interactive CLI.
- Linear handoff: MON-316 — https://linear.app/monkhouseandcompany/issue/MON-316/graphiti-falkordb-memory-layer-implementation-plan
