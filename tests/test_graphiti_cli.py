from __future__ import annotations

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
