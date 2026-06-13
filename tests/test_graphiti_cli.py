from __future__ import annotations

import json
from typing import ClassVar

from click.testing import CliRunner

from memsearch import cli as cli_module
from memsearch.cli import cli
from memsearch.config import MemSearchConfig


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

    def search_memory_facts(self, query, *, group_id="", limit=5):
        self.calls.append(("search_memory_facts", {"query": query, "group_id": group_id, "limit": limit}))
        return {"facts": [{"fact": "Graphiti uses FalkorDB"}]}

    def search_nodes(self, query, *, group_id="", limit=5):
        self.calls.append(("search_nodes", {"query": query, "group_id": group_id, "limit": limit}))
        return {"nodes": [{"name": "Graphiti", "summary": "Temporal memory graph"}]}

    def add_memory(self, episode, *, group_id=""):
        self.calls.append(("add_memory", {"name": episode.name, "group_id": group_id}))
        return {"message": "queued"}


class BrokenGraphitiClient(FakeGraphitiClient):
    def search_memory_facts(self, query, *, group_id="", limit=5):
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
    assert "Graphiti uses FalkorDB" in result.output
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
    assert payload["graph"]["facts"][0]["fact"] == "Graphiti uses FalkorDB"
    assert FakeMemSearch.instances[0].calls[0]["query"] == "MON-316"
    assert FakeGraphitiClient.instances[0].calls == [
        ("search_memory_facts", {"query": "MON-316", "group_id": "ms_memsearch_active_curated_v1", "limit": 5}),
        ("search_nodes", {"query": "MON-316", "group_id": "ms_memsearch_active_curated_v1", "limit": 5}),
    ]


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
