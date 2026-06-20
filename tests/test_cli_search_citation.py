from __future__ import annotations

import json

from click.testing import CliRunner

from memsearch import core as core_module
from memsearch.cli import cli


class FakeEmbedder:
    model_name = "fake-model"
    dimension = 2

    async def embed(self, texts):
        return [[0.0, 1.0] for _ in texts]


class FakeStore:
    """Fake MilvusStore returning one dated result with a line range."""

    def __init__(self, *args, **kwargs):
        pass

    def search(self, query_embedding, *, query_text="", top_k=10, filter_expr=""):
        return [
            {
                "content": "We set the third pricing tier at £37.",
                "score": 0.9,
                "heading": "Pricing",
                "source": "/x/.memsearch/memory/2026-06-10.md",
                "chunk_hash": "abc",
                "start_line": 5,
                "end_line": 7,
            }
        ]

    def close(self) -> None:
        pass


def _write_config(tmp_path, monkeypatch):
    """Point the global config at a tmp file with Dom's citation author."""
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[citation]\nauthor = "Dominic Monkhouse (dominicmonkhouse)"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("memsearch.config.GLOBAL_CONFIG_PATH", cfg_path)
    monkeypatch.setattr("memsearch.config.PROJECT_CONFIG_PATH", tmp_path / "nope.toml")


def _patch_fakes(monkeypatch):
    def fake_get_provider(*args, **kwargs):
        return FakeEmbedder()

    monkeypatch.setattr(core_module, "get_provider", fake_get_provider)
    monkeypatch.setattr(core_module, "MilvusStore", FakeStore)


def test_search_human_output_shows_citation(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch)
    _patch_fakes(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "pricing tier", "--no-graph"])

    assert result.exit_code == 0, result.output
    assert "decided by Dominic Monkhouse" in result.output
    assert "2026-" in result.output
    assert ":5-7" in result.output


def test_search_json_output_carries_citation_fields(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch)
    _patch_fakes(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "pricing tier", "--no-graph", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert payload[0]["author"] == "Dominic Monkhouse (dominicmonkhouse)"
    assert "days_since" in payload[0]
