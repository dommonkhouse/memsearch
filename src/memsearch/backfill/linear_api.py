from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"


class LinearApiError(RuntimeError):
    pass


Transport = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class LinearIssue:
    id: str
    identifier: str
    title: str
    url: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    state: str = ""
    team: str = ""
    assignee: str = ""
    labels: tuple[str, ...] = ()
    comments: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_graphql(cls, data: dict[str, Any]) -> LinearIssue:
        labels = tuple(
            str(label.get("name") or "") for label in (data.get("labels") or {}).get("nodes", []) if label.get("name")
        )
        comments = tuple(
            {
                "id": str(comment.get("id") or ""),
                "body": str(comment.get("body") or ""),
                "created_at": str(comment.get("createdAt") or ""),
                "updated_at": str(comment.get("updatedAt") or ""),
                "user": str((comment.get("user") or {}).get("name") or ""),
            }
            for comment in (data.get("comments") or {}).get("nodes", [])
        )
        return cls(
            id=str(data.get("id") or ""),
            identifier=str(data.get("identifier") or ""),
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            description=str(data.get("description") or ""),
            created_at=str(data.get("createdAt") or ""),
            updated_at=str(data.get("updatedAt") or ""),
            state=str((data.get("state") or {}).get("name") or ""),
            team=str((data.get("team") or {}).get("key") or (data.get("team") or {}).get("name") or ""),
            assignee=str((data.get("assignee") or {}).get("name") or ""),
            labels=labels,
            comments=comments,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "identifier": self.identifier,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state": self.state,
            "team": self.team,
            "assignee": self.assignee,
            "labels": list(self.labels),
            "comments": list(self.comments),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> LinearIssue:
        return cls(
            id=str(data.get("id") or ""),
            identifier=str(data.get("identifier") or ""),
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            description=str(data.get("description") or ""),
            created_at=str(data.get("created_at") or data.get("createdAt") or ""),
            updated_at=str(data.get("updated_at") or data.get("updatedAt") or ""),
            state=str(data.get("state") or ""),
            team=str(data.get("team") or ""),
            assignee=str(data.get("assignee") or ""),
            labels=tuple(str(label) for label in data.get("labels") or []),
            comments=tuple(dict(comment) for comment in data.get("comments") or []),
        )


class LinearApiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        url: str = LINEAR_GRAPHQL_URL,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("LINEAR_API_KEY", "")
        if not self.api_key:
            raise LinearApiError("LINEAR_API_KEY is required")
        self.url = url
        self._transport = transport
        self._sleep = sleep

    def updated_issues(self, *, since: str, limit: int | None = None) -> list[LinearIssue]:
        first = min(limit or 50, 100)
        query = """
        query($first: Int!, $after: String, $since: DateTimeOrDuration!) {
          issues(
            first: $first,
            after: $after,
            filter: { updatedAt: { gte: $since } },
            orderBy: updatedAt
          ) {
            nodes {
              id
              identifier
              title
              url
              description
              createdAt
              updatedAt
              state { name }
              team { key name }
              assignee { name }
              labels(first: 20) { nodes { name } }
              comments(first: 50) {
                nodes { id body createdAt updatedAt user { name } }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """
        issues: list[LinearIssue] = []
        after = None
        while True:
            data = self._graphql(query, {"first": first, "after": after, "since": since})
            page = data["issues"]
            issues.extend(LinearIssue.from_graphql(node) for node in page.get("nodes", []))
            if limit is not None and len(issues) >= limit:
                return issues[:limit]
            info = page.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                return issues
            after = info.get("endCursor")
            if not after:
                return issues

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = {"query": query, "variables": variables}
        headers = {"content-type": "application/json", "authorization": self.api_key}
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                if self._transport is not None:
                    body = self._transport(query, variables, headers)
                else:
                    with httpx.Client(timeout=60) as client:
                        response = client.post(self.url, headers=headers, json=payload)
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after")
                        delay = float(retry_after) if retry_after else 0.5 * (attempt + 1)
                        self._sleep(delay)
                        last_error = LinearApiError("Linear API rate limited")
                        continue
                    if response.status_code >= 400:
                        raise LinearApiError(
                            f"Linear API request failed: HTTP {response.status_code} {response.text[:300]}"
                        )
                    body = response.json()
                if body.get("errors"):
                    raise LinearApiError(json.dumps(body["errors"], sort_keys=True))
                return body["data"]
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                last_error = exc
            self._sleep(0.5 * (attempt + 1))
        raise LinearApiError("Linear API request failed after retries") from last_error
