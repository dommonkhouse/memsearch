import pytest

from memsearch.graphiti.client import GraphitiClient, GraphitiClientError
from memsearch.graphiti.episodes import GraphitiEpisode


class FakeTransport:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments or {}))
        if name == "get_status":
            return {"status": "ok"}
        if name == "add_memory":
            return {"message": "queued"}
        if name == "search_memory_facts":
            return {"facts": [{"fact": "Graphiti uses FalkorDB", "episodes": ["episode-1"]}]}
        if name == "search_nodes":
            return {"nodes": [{"name": "Graphiti", "uuid": "node-1"}]}
        if name == "get_episodes":
            return {"episodes": [{"uuid": "episode-1", "name": "memory.md:3"}]}
        raise AssertionError(f"unexpected tool {name}")


def _episode() -> GraphitiEpisode:
    return GraphitiEpisode(
        name="memory.md:3",
        body="Graphiti plus FalkorDB",
        source_description="memsearch markdown memory",
        reference_time=None,
        metadata={"source": "/tmp/memory.md", "start_line": 3, "end_line": 7},
        content_hash="abc",
    )


def test_get_status_calls_graphiti_tool():
    transport = FakeTransport()
    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=transport)

    assert client.get_status() == {"status": "ok"}
    assert transport.calls == [("get_status", {})]


def test_add_memory_calls_graphiti_tool_with_provenance():
    transport = FakeTransport()
    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=transport)

    result = client.add_memory(_episode(), group_id="ms_memsearch_ae2d4f9b")

    assert result == {"message": "queued"}
    assert transport.calls[0][0] == "add_memory"
    assert transport.calls[0][1]["name"] == "memory.md:3"
    assert transport.calls[0][1]["episode_body"] == "Graphiti plus FalkorDB"
    assert transport.calls[0][1]["group_id"] == "ms_memsearch_ae2d4f9b"
    assert transport.calls[0][1]["source"] == "text"
    assert "memsearch markdown memory" in transport.calls[0][1]["source_description"]
    assert "/tmp/memory.md" in transport.calls[0][1]["source_description"]
    assert "content_hash=abc" in transport.calls[0][1]["source_description"]
    assert "reference_time" not in transport.calls[0][1]


def test_search_memory_facts_uses_current_graphiti_schema():
    transport = FakeTransport()
    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=transport)

    result = client.search_memory_facts("Graphiti", group_id="ms_memsearch_ae2d4f9b", limit=5)

    assert result["facts"][0]["episodes"] == ["episode-1"]
    assert transport.calls == [
        (
            "search_memory_facts",
            {"query": "Graphiti", "group_ids": ["ms_memsearch_ae2d4f9b"], "max_facts": 5},
        )
    ]


def test_search_nodes_uses_current_graphiti_schema():
    transport = FakeTransport()
    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=transport)

    result = client.search_nodes("Graphiti", group_id="ms_memsearch_ae2d4f9b", limit=3)

    assert result["nodes"][0]["uuid"] == "node-1"
    assert transport.calls == [
        (
            "search_nodes",
            {"query": "Graphiti", "group_ids": ["ms_memsearch_ae2d4f9b"], "max_nodes": 3},
        )
    ]


def test_get_episodes_filters_by_group_id():
    transport = FakeTransport()
    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=transport)

    result = client.get_episodes(group_id="ms_memsearch_ae2d4f9b", limit=2)

    assert result["episodes"][0]["uuid"] == "episode-1"
    assert transport.calls == [
        (
            "get_episodes",
            {"group_ids": ["ms_memsearch_ae2d4f9b"], "max_episodes": 2},
        )
    ]


def test_graphiti_error_payload_raises_client_error():
    class ErrorTransport:
        def call_tool(self, name, arguments=None):
            return {"error": "bad group"}

    client = GraphitiClient("http://127.0.0.1:8018/mcp", transport=ErrorTransport())

    with pytest.raises(GraphitiClientError, match="bad group"):
        client.get_status()
