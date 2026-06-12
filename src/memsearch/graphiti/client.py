"""Synchronous Graphiti MCP client helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from .episodes import GraphitiEpisode


class GraphitiTransport(Protocol):
    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a Graphiti MCP tool and return its JSON object response."""


class GraphitiClientError(RuntimeError):
    """Raised when the Graphiti MCP client cannot complete a request."""


@dataclass
class McpStreamableHttpTransport:
    endpoint: str
    host_header: str = ""
    timeout_seconds: int = 120

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return asyncio.run(self._call_tool(name, arguments or {}))

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ModuleNotFoundError as exc:
            raise GraphitiClientError(
                "Graphiti MCP client dependency is missing. Install the mcp package or use a venv that includes it."
            ) from exc

        headers = {"Host": self.host_header} if self.host_header else None
        try:
            async with streamablehttp_client(
                self.endpoint,
                headers=headers,
                timeout=self.timeout_seconds,
                sse_read_timeout=self.timeout_seconds,
            ) as (read_stream, write_stream, _), ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
        except Exception as exc:
            raise GraphitiClientError(f"Graphiti MCP tool {name!r} failed: {exc}") from exc

        if not getattr(result, "content", None):
            return {}

        text = "\n".join(getattr(part, "text", "") for part in result.content).strip()
        if not text:
            return {}

        import json

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GraphitiClientError(f"Graphiti MCP tool {name!r} returned non-JSON content: {text}") from exc
        if not isinstance(data, dict):
            raise GraphitiClientError(f"Graphiti MCP tool {name!r} returned non-object JSON")
        return data


class GraphitiClient:
    def __init__(
        self,
        endpoint: str,
        *,
        host_header: str = "",
        timeout_seconds: int = 120,
        transport: GraphitiTransport | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.transport = transport or McpStreamableHttpTransport(
            endpoint=endpoint,
            host_header=host_header,
            timeout_seconds=timeout_seconds,
        )

    def get_status(self) -> dict[str, Any]:
        return self._checked(self.transport.call_tool("get_status", {}))

    def add_memory(self, episode: GraphitiEpisode, *, group_id: str = "") -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "name": episode.name,
            "episode_body": episode.body,
            "source": "text",
            "source_description": self._source_description(episode),
        }
        if group_id:
            arguments["group_id"] = group_id
        if episode.reference_time:
            arguments["reference_time"] = episode.reference_time
        return self._checked(self.transport.call_tool("add_memory", arguments))

    def search_memory_facts(self, query: str, *, group_id: str = "", limit: int = 5) -> dict[str, Any]:
        arguments: dict[str, Any] = {"query": query, "max_facts": limit}
        if group_id:
            arguments["group_ids"] = [group_id]
        return self._checked(self.transport.call_tool("search_memory_facts", arguments))

    def search_nodes(self, query: str, *, group_id: str = "", limit: int = 5) -> dict[str, Any]:
        arguments: dict[str, Any] = {"query": query, "max_nodes": limit}
        if group_id:
            arguments["group_ids"] = [group_id]
        return self._checked(self.transport.call_tool("search_nodes", arguments))

    def get_episodes(self, *, group_id: str = "", limit: int = 10) -> dict[str, Any]:
        arguments: dict[str, Any] = {"max_episodes": limit}
        if group_id:
            arguments["group_ids"] = [group_id]
        return self._checked(self.transport.call_tool("get_episodes", arguments))

    def clear_graph(self, *, group_id: str) -> dict[str, Any]:
        return self._checked(self.transport.call_tool("clear_graph", {"group_ids": [group_id]}))

    @staticmethod
    def _checked(result: dict[str, Any]) -> dict[str, Any]:
        if "error" in result:
            raise GraphitiClientError(str(result["error"]))
        return result

    @staticmethod
    def _source_description(episode: GraphitiEpisode) -> str:
        source = episode.metadata.get("source", "")
        start_line = episode.metadata.get("start_line", "")
        end_line = episode.metadata.get("end_line", "")
        parts = [
            episode.source_description,
            f"source={source}",
            f"lines={start_line}-{end_line}",
            f"content_hash={episode.content_hash}",
        ]
        return " | ".join(str(part) for part in parts if part)
