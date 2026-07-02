from __future__ import annotations

import json
from contextlib import contextmanager
from typing import ClassVar

from click.testing import CliRunner

from memsearch import cli as cli_module
from memsearch.cli import cli
from memsearch.config import MemSearchConfig
from memsearch.graphiti.watchdog import WatchdogCheck


class FakeGraphitiClient:
    instances: ClassVar[list] = []

    def __init__(self, endpoint, *, host_header="", timeout_seconds=120):
        self.endpoint = endpoint
        self.host_header = host_header
        self.timeout_seconds = timeout_seconds
        self.calls = []
        self.instances.append(self)

    def get_status(self):
        self.calls.append(("get_status", {}))
        return {"status": "ok", "message": "Graphiti is healthy"}

    def search_memory_facts(self, query, *, group_id="", limit=5, center_node_uuid=None):
        call = {"query": query, "group_id": group_id, "limit": limit}
        if center_node_uuid:
            call["center_node_uuid"] = center_node_uuid
        self.calls.append(("search_memory_facts", call))
        if center_node_uuid:
            return {
                "facts": [
                    {
                        "fact": "MON-316 centred Graphiti relationship detail uses FalkorDB.",
                        "uuid": "centered-fact",
                    }
                ]
            }
        return {
            "facts": [
                {"fact": "MON-316 uses Graphiti with FalkorDB", "uuid": "base-fact"},
                {
                    "fact": "Graphiti will be checked with ruff during the plan execution.",
                    "expired_at": "2026-06-12T22:02:37.045366Z",
                    "invalid_at": "2026-06-11T10:23:41.342000Z",
                },
                {"fact": "MON-310 owns unrelated CMM taxonomy cleanup."},
            ]
        }

    def search_nodes(self, query, *, group_id="", limit=5):
        self.calls.append(("search_nodes", {"query": query, "group_id": group_id, "limit": limit}))
        return {
            "nodes": [
                {"name": "Graphiti", "uuid": "graphiti-node", "summary": "Temporal memory graph for MON-316"},
                {"name": "Graphiti", "uuid": "graphiti-duplicate", "summary": "Duplicate lower quality node"},
                {"name": "MON-310", "uuid": "mon310-node", "summary": "Unrelated CMM taxonomy cleanup"},
            ]
        }

    def add_memory(self, episode, *, group_id=""):
        self.calls.append(("add_memory", {"name": episode.name, "group_id": group_id}))
        return {"message": "queued"}

    def clear_graph(self, *, group_id):
        self.calls.append(("clear_graph", {"group_id": group_id}))
        return {"message": "cleared"}


class BrokenGraphitiClient(FakeGraphitiClient):
    def search_memory_facts(self, query, *, group_id="", limit=5, center_node_uuid=None):
        from memsearch.graphiti.client import GraphitiClientError

        raise GraphitiClientError("sidecar offline")


class FakeMemSearch:
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        self.instances.append(self)

    async def search(self, query, *, top_k=10, source_prefix=None):
        self.calls.append({"query": query, "top_k": top_k, "source_prefix": source_prefix})
        return [
            {
                "chunk_hash": "exact-mon-316",
                "content": "MON-316 exact issue reference",
                "source": "/tmp/linear.md",
                "heading": "MON-316",
                "score": 0.99,
            },
            {
                "chunk_hash": "branch",
                "content": "branch dom/mon-316-graphiti-falkordb",
                "source": "/tmp/status.md",
                "heading": "Branch",
                "score": 0.88,
            },
        ]

    def close(self):
        self.calls.append({"close": True})


def _cfg(tmp_path) -> MemSearchConfig:
    cfg = MemSearchConfig()
    cfg.graphiti.endpoint = "http://graphiti.example/mcp"
    cfg.graphiti.host_header = "127.0.0.1:18018"
    cfg.graphiti.group_id = "ms_test"
    cfg.graphiti.manifest_path = str(tmp_path / "manifest.json")
    return cfg


def test_graph_status_uses_graphiti_config(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["graph-status"])

    assert result.exit_code == 0
    assert "Graphiti is healthy" in result.output
    client = FakeGraphitiClient.instances[0]
    assert client.endpoint == "http://graphiti.example/mcp"
    assert client.host_header == "127.0.0.1:18018"


def test_graph_search_outputs_facts_and_nodes(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["graph-search", "Graphiti"])

    assert result.exit_code == 0
    assert "MON-316 uses Graphiti with FalkorDB" in result.output
    assert "Temporal memory graph" in result.output
    assert FakeGraphitiClient.instances[0].calls == [
        ("search_memory_facts", {"query": "Graphiti", "group_id": "ms_test", "limit": 5}),
        ("search_nodes", {"query": "Graphiti", "group_id": "ms_test", "limit": 5}),
    ]


def test_graph_index_queues_new_episodes_and_writes_manifest(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    memory = tmp_path / "memory.md"
    memory.write_text("### Decision\n\nUse Graphiti with FalkorDB.\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["graph-index", str(memory)])

    assert result.exit_code == 0
    assert "Queued 1 Graphiti episode(s)" in result.output
    assert "Skipped 0 unchanged episode(s)" in result.output
    assert FakeGraphitiClient.instances[0].calls[0][0] == "add_memory"
    assert (tmp_path / "manifest.json").is_file()

    second = CliRunner().invoke(cli, ["graph-index", str(memory)])

    assert second.exit_code == 0
    assert "Queued 0 Graphiti episode(s)" in second.output
    assert "Skipped 1 unchanged episode(s)" in second.output


def test_graph_index_locks_manifest_for_real_run(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    memory = tmp_path / "memory.md"
    memory.write_text("### Decision\n\nUse Graphiti with FalkorDB.\n", encoding="utf-8")
    lock_paths = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    @contextmanager
    def fake_manifest_lock(path):
        lock_paths.append(path)
        yield

    monkeypatch.setattr(cli_module, "_graphiti_manifest_lock", fake_manifest_lock)

    result = CliRunner().invoke(cli, ["graph-index", str(memory)])

    assert result.exit_code == 0
    assert lock_paths == [str(tmp_path / "manifest.json")]


def test_graph_index_curated_dry_run_uses_separate_manifest_and_group(monkeypatch, tmp_path):
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "2026-06.md"
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-12.md"
    linear.parent.mkdir(parents=True, exist_ok=True)
    raw.parent.mkdir(parents=True, exist_ok=True)
    linear.write_text(
        "### MON-316\n\nGraphiti FalkorDB sidecar.\n\n### MON-259\n\nExact vector lookup control.\n",
        encoding="utf-8",
    )
    raw.write_text("### Raw chat\n\nNoisy chat dump.\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(cli, ["graph-index-curated", str(tmp_path / ".memsearch" / "memory"), "--dry-run"])

    assert result.exit_code == 0
    assert "2 scanned, 1 selected, 1 excluded" in result.output
    assert "Group: ms_memsearch_active_curated_v1" in result.output
    assert "Manifest: .memsearch/graphiti-curated-manifest.json" in result.output


def test_graph_index_curated_requires_real_run_cap(monkeypatch, tmp_path):
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "2026-06.md"
    linear.parent.mkdir(parents=True, exist_ok=True)
    linear.write_text(
        "### MON-316\n\nGraphiti FalkorDB sidecar.\n\n### MON-259\n\nExact vector lookup control.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(cli, ["graph-index-curated", str(tmp_path / ".memsearch" / "memory")])

    assert result.exit_code == 1
    assert "Refusing uncapped curated Graphiti ingestion" in result.stderr


def test_graph_index_curated_queues_with_cap_and_curated_manifest(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "2026-06.md"
    manifest = tmp_path / ".memsearch" / "graphiti-curated-manifest.json"
    linear.parent.mkdir(parents=True, exist_ok=True)
    linear.write_text(
        "### MON-316\n\nGraphiti FalkorDB sidecar.\n\n### MON-259\n\nExact vector lookup control.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(
        cli,
        [
            "graph-index-curated",
            str(tmp_path / ".memsearch" / "memory"),
            "--limit",
            "1",
            "--manifest-path",
            str(manifest),
        ],
    )

    assert result.exit_code == 0
    assert "Queued 1 curated Graphiti episode(s)" in result.output
    assert "Deferred 1 episode(s) by limit." in result.output
    assert "Group: ms_memsearch_active_curated_v1" in result.output
    assert manifest.is_file()
    assert FakeGraphitiClient.instances[0].calls[0][1]["group_id"] == "ms_memsearch_active_curated_v1"


def test_graph_index_curated_locks_manifest_for_real_run(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    linear = tmp_path / ".memsearch" / "memory" / "linear" / "2026-06.md"
    manifest = tmp_path / ".memsearch" / "graphiti-curated-manifest.json"
    linear.parent.mkdir(parents=True, exist_ok=True)
    linear.write_text(
        "### MON-316\n\nGraphiti FalkorDB sidecar.\n\n### MON-259\n\nExact vector lookup control.\n",
        encoding="utf-8",
    )
    lock_paths = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    @contextmanager
    def fake_manifest_lock(path):
        lock_paths.append(path)
        yield

    monkeypatch.setattr(cli_module, "_graphiti_manifest_lock", fake_manifest_lock)

    result = CliRunner().invoke(
        cli,
        [
            "graph-index-curated",
            str(tmp_path / ".memsearch" / "memory"),
            "--limit",
            "1",
            "--manifest-path",
            str(manifest),
        ],
    )

    assert result.exit_code == 0
    assert lock_paths == [str(manifest)]


def test_search_include_graph_preserves_vector_results_and_adds_curated_graph(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["search", "MON-316", "--include-graph", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vector"][0]["chunk_hash"] == "exact-mon-316"
    assert payload["vector"][0]["heading"] == "MON-316"
    assert payload["graph"]["facts"][0]["fact"] == "MON-316 uses Graphiti with FalkorDB"
    assert payload["graph"]["facts"][1]["fact"] == "MON-316 centred Graphiti relationship detail uses FalkorDB."
    assert payload["graph"]["facts"][1]["graph_center_node"] == "Graphiti"
    assert all("ruff" not in fact["fact"] for fact in payload["graph"]["facts"])
    assert all("MON-310" not in fact["fact"] for fact in payload["graph"]["facts"])
    assert [node["name"] for node in payload["graph"]["nodes"]] == ["Graphiti"]
    assert FakeMemSearch.instances[0].calls[0]["query"] == "MON-316"
    assert FakeGraphitiClient.instances[0].calls == [
        ("search_nodes", {"query": "MON-316", "group_id": "ms_memsearch_active_curated_v1", "limit": 15}),
        ("search_memory_facts", {"query": "MON-316", "group_id": "ms_memsearch_active_curated_v1", "limit": 15}),
        (
            "search_memory_facts",
            {
                "query": "MON-316",
                "group_id": "ms_memsearch_active_curated_v1",
                "limit": 15,
                "center_node_uuid": "graphiti-node",
            },
        ),
    ]


def test_search_defaults_to_graph_with_vector_results_primary(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["search", "MON-316", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vector"][0]["chunk_hash"] == "exact-mon-316"
    assert payload["graph"]["facts"][0]["fact"] == "MON-316 uses Graphiti with FalkorDB"


def test_search_no_graph_returns_vector_only_json(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["search", "MON-316", "--no-graph", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert payload[0]["chunk_hash"] == "exact-mon-316"
    assert FakeGraphitiClient.instances == []


def test_search_include_graph_falls_back_to_vector_when_graphiti_fails(monkeypatch, tmp_path):
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", BrokenGraphitiClient)

    result = CliRunner().invoke(cli, ["search", "relationship query", "--include-graph", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vector"][0]["chunk_hash"] == "exact-mon-316"
    assert payload["graph"] == {"facts": [], "nodes": []}
    assert payload["graph_error"] == "sidecar offline"


def test_graph_watchdog_dry_run_reports_restart_without_executing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: calls.extend(commands))

    result = CliRunner().invoke(cli, ["graph-watchdog", "--dry-run", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["decision"]["action"] == "restart_graphiti"
    assert calls == []


def test_graph_watchdog_execute_runs_recovery(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: calls.extend(commands))

    result = CliRunner().invoke(cli, ["graph-watchdog", "--execute", "--json-output"])

    assert result.exit_code == 0
    assert any("start-graphiti-mon316.sh" in command for command in calls)


def test_graph_watchdog_records_consecutive_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "memsearch.graphiti.watchdog.collect_checks",
        lambda: [WatchdogCheck("local_health", False, "connection refused")],
    )
    monkeypatch.setattr("memsearch.graphiti.watchdog.run_recovery_commands", lambda commands: [])

    state = tmp_path / "watchdog.json"

    result = CliRunner().invoke(cli, ["graph-watchdog", "--dry-run", "--state-path", str(state), "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(state.read_text())
    assert payload["consecutive_failures"] == 1
    assert payload["alert_required"] is False


def test_graph_candidate_report_writes_report(tmp_path):
    seed = tmp_path / "docs" / "graphiti-curated-seeds" / "seed.md"
    output = tmp_path / "report.md"
    seed.parent.mkdir(parents=True)
    seed.write_text("### Current\n\nClassification: current\n\nGraphiti uses FalkorDB.\n\nEvidence: docs/graphiti-falkordb.md\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["graph-candidate-report", str(seed), "--output", str(output)])

    assert result.exit_code == 0
    assert output.is_file()
    body = output.read_text()
    assert "Accepted" in body
    assert "Classification: current" in body


def test_graph_candidate_report_review_sources_uses_filtered_source_paths(monkeypatch, tmp_path):
    source = tmp_path / "reviewed.md"
    output = tmp_path / "report.md"
    source.write_text(
        "### Current\n\nClassification: current\n\nGraphiti uses FalkorDB.\n\nEvidence: docs/graphiti-falkordb.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("memsearch.graphiti.review_sources.existing_review_source_paths", lambda: [source])

    result = CliRunner().invoke(cli, ["graph-candidate-report", "--review-sources", "--output", str(output)])

    assert result.exit_code == 0
    assert output.is_file()
    assert str(source) in output.read_text(encoding="utf-8")


def test_graph_candidate_report_review_sources_rejects_positional_paths(tmp_path):
    source = tmp_path / "reviewed.md"
    output = tmp_path / "report.md"
    source.write_text("Classification: current\nEvidence: docs/example.md\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli, ["graph-candidate-report", str(source), "--review-sources", "--output", str(output)]
    )

    assert result.exit_code == 1
    assert "--review-sources cannot be combined" in result.output


def test_graph_review_worklist_writes_markdown_and_json_from_report(tmp_path):
    source = tmp_path / "source.md"
    report = tmp_path / "report.md"
    output = tmp_path / "worklist.md"
    json_output = tmp_path / "worklist.json"
    source.write_text("Classification: missing\nUseful context.\n", encoding="utf-8")
    report.write_text(
        f"""# Graphiti candidate report

## Accepted

No accepted candidates.

## Rejected

- Source: {source}
  - Classification: missing
  - Status: rejected_missing_classification
  - Detail: missing Classification marker
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "graph-review-worklist",
            "--candidate-report",
            str(report),
            "--output",
            str(output),
            "--json-output-path",
            str(json_output),
        ],
    )

    assert result.exit_code == 0
    assert "needs_classification: 1" in result.output
    assert "needs_classification" in output.read_text(encoding="utf-8")
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["items"][0]["state"] == "needs_classification"


def test_graph_review_worklist_does_not_construct_graphiti_client(monkeypatch, tmp_path):
    source = tmp_path / "source.md"
    report = tmp_path / "report.md"
    output = tmp_path / "worklist.md"
    json_output = tmp_path / "worklist.json"
    source.write_text("Classification: missing\nUseful context.\n", encoding="utf-8")
    report.write_text(
        f"""# Graphiti candidate report

## Accepted

No accepted candidates.

## Rejected

- Source: {source}
  - Classification: missing
  - Status: rejected_missing_classification
  - Detail: missing Classification marker
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "memsearch.graphiti.client.GraphitiClient",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Graphiti client constructed")),
    )

    result = CliRunner().invoke(
        cli,
        [
            "graph-review-worklist",
            "--candidate-report",
            str(report),
            "--output",
            str(output),
            "--json-output-path",
            str(json_output),
        ],
    )

    assert result.exit_code == 0


def test_graph_review_worklist_refuses_blocked_source_paths(tmp_path):
    report = tmp_path / "report.md"
    output = tmp_path / "worklist.md"
    json_output = tmp_path / "worklist.json"
    blocked_sources = [
        "/Users/dominicmonkhouse/Projects/claude-config/memory/feedback/workflow.md",
        "/Users/dominicmonkhouse/Projects/claude-config/memory/feedback_example.md",
        "/Users/dominicmonkhouse/Projects/claude-config/memory/README.md",
    ]
    report.write_text(
        "# Graphiti candidate report\n\n## Accepted\n\nNo accepted candidates.\n\n## Rejected\n\n"
        + "\n".join(
            f"""- Source: {source}
  - Classification: missing
  - Status: rejected_missing_classification
  - Detail: missing Classification marker"""
            for source in blocked_sources
        )
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "graph-review-worklist",
            "--candidate-report",
            str(report),
            "--output",
            str(output),
            "--json-output-path",
            str(json_output),
        ],
    )

    assert result.exit_code == 1
    assert "refusing blocked Graphiti review source" in result.output
    assert not output.exists()
    assert not json_output.exists()


def test_graph_index_curated_dry_run_excludes_raw_daily_memory(monkeypatch, tmp_path):
    raw = tmp_path / ".memsearch" / "memory" / "2026-06-14.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("### Raw\n\nTroubleshooting notes.\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(cli, ["graph-index-curated", str(tmp_path / ".memsearch" / "memory"), "--dry-run"])

    assert result.exit_code == 0
    assert "0 selected" in result.output


def test_graph_clear_group_requires_matching_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))

    result = CliRunner().invoke(
        cli,
        ["graph-clear-group", "--group-id", "ms_memsearch_active_curated_v1", "--confirm-group-id", "wrong", "--execute"],
    )

    assert result.exit_code == 1
    assert "confirmation" in result.output.lower()


def test_graph_clear_group_execute_calls_client(monkeypatch, tmp_path):
    calls = []

    class ClearClient(FakeGraphitiClient):
        def clear_graph(self, *, group_id):
            calls.append(group_id)
            return {"message": "cleared"}

    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", ClearClient)

    result = CliRunner().invoke(
        cli,
        [
            "graph-clear-group",
            "--group-id",
            "ms_memsearch_active_curated_v1",
            "--confirm-group-id",
            "ms_memsearch_active_curated_v1",
            "--execute",
        ],
    )

    assert result.exit_code == 0
    assert calls == ["ms_memsearch_active_curated_v1"]


def test_graph_backup_dry_run_prints_non_destructive_commands():
    result = CliRunner().invoke(cli, ["graph-backup"])

    assert result.exit_code == 0
    assert "graphiti_mon316_falkordb_data" in result.output
    assert "/var/lib/falkordb/data" in result.output
    assert "down -v" not in result.output


def test_graph_backup_execute_calls_runner(monkeypatch, tmp_path):
    from memsearch.graphiti.backup import BackupResult

    backup_path = tmp_path / "backup"
    metadata_path = backup_path / "metadata.json"
    monkeypatch.setattr(
        "memsearch.graphiti.backup.run_backup",
        lambda *, root, retain_days, prune_to_trash: BackupResult(path=backup_path, metadata_path=metadata_path),
    )

    result = CliRunner().invoke(cli, ["graph-backup", "--backup-root", str(tmp_path), "--execute"])

    assert result.exit_code == 0
    assert str(backup_path) in result.output


def test_graph_eval_case_filter_runs_only_named_case(monkeypatch, tmp_path):
    FakeGraphitiClient.instances = []
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)
    monkeypatch.setattr("memsearch.graphiti.client.GraphitiClient", FakeGraphitiClient)

    result = CliRunner().invoke(cli, ["graph-eval", "--case", "exact-mon-316", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["passed"] == 1
    assert payload["failed"] == 0
    assert [case["name"] for case in payload["cases"]] == ["exact-mon-316"]
    assert [call["query"] for call in FakeMemSearch.instances[0].calls if "query" in call] == ["MON-316"]


def test_graph_eval_case_filter_rejects_unknown_case(monkeypatch, tmp_path):
    FakeMemSearch.instances = []
    monkeypatch.setattr(cli_module, "resolve_config", lambda _overrides=None: _cfg(tmp_path))
    monkeypatch.setattr("memsearch.core.MemSearch", FakeMemSearch)

    result = CliRunner().invoke(cli, ["graph-eval", "--case", "missing-case"])

    assert result.exit_code == 2
    assert "Unknown graph evaluation case(s): missing-case" in result.stderr
