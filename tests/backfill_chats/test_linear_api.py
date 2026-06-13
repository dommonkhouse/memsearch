from __future__ import annotations

from memsearch.backfill.linear_api import LinearApiClient


def test_linear_client_fetches_updated_issues_with_comments() -> None:
    calls: list[tuple[str, dict, dict[str, str]]] = []

    def transport(query: str, variables: dict, headers: dict[str, str]) -> dict:
        calls.append((query, variables, headers))
        return {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-id",
                            "identifier": "MON-318",
                            "title": "Freshness",
                            "url": "https://linear.app/issue/MON-318",
                            "description": "Build it",
                            "createdAt": "2026-06-10T00:00:00Z",
                            "updatedAt": "2026-06-11T00:00:00Z",
                            "state": {"name": "Todo"},
                            "team": {"key": "MON", "name": "Monkhouse"},
                            "assignee": {"name": "Dominic"},
                            "labels": {"nodes": [{"name": "memory"}]},
                            "comments": {
                                "nodes": [
                                    {
                                        "id": "comment-id",
                                        "body": "Found in Linear",
                                        "createdAt": "2026-06-11T01:00:00Z",
                                        "updatedAt": "2026-06-11T01:00:00Z",
                                        "user": {"name": "Dominic"},
                                    }
                                ]
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

    client = LinearApiClient(api_key="linear-key", transport=transport)

    issues = client.updated_issues(since="2026-06-10T00:00:00Z", limit=10)

    assert issues[0].identifier == "MON-318"
    assert issues[0].comments[0]["body"] == "Found in Linear"
    assert calls[0][1]["since"] == "2026-06-10T00:00:00Z"
    assert calls[0][2]["authorization"] == "linear-key"
