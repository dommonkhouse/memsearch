from __future__ import annotations

from pathlib import Path

import pytest

from memsearch.config import (
    MemSearchConfig,
    get_config_value,
    load_config_file,
    resolve_config,
    set_config_value,
)


def test_graphiti_config_defaults_disabled() -> None:
    cfg = MemSearchConfig()

    assert cfg.graphiti.enabled is False
    assert cfg.graphiti.transport == "mcp-streamable-http"
    assert cfg.graphiti.endpoint == "http://127.0.0.1:8018/mcp"
    assert cfg.graphiti.host_header == ""
    assert cfg.graphiti.group_id == ""
    assert cfg.graphiti.batch_size == 10
    assert cfg.graphiti.request_timeout_seconds == 120
    assert cfg.graphiti.manifest_path == ".memsearch/graphiti-manifest.json"


def test_graphiti_config_set_get_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr("memsearch.config.GLOBAL_CONFIG_PATH", cfg_path)
    monkeypatch.setattr("memsearch.config.PROJECT_CONFIG_PATH", tmp_path / "nope.toml")

    set_config_value("graphiti.enabled", "true")
    set_config_value("graphiti.endpoint", "http://127.0.0.1:8018/mcp")
    set_config_value("graphiti.host_header", "127.0.0.1:18018")
    set_config_value("graphiti.transport", "mcp-streamable-http")
    set_config_value("graphiti.request_timeout_seconds", "60")

    cfg = resolve_config()

    assert cfg.graphiti.enabled is True
    assert cfg.graphiti.endpoint == "http://127.0.0.1:8018/mcp"
    assert cfg.graphiti.host_header == "127.0.0.1:18018"
    assert cfg.graphiti.transport == "mcp-streamable-http"
    assert cfg.graphiti.request_timeout_seconds == 60
    assert get_config_value("graphiti.enabled", cfg) is True
    assert get_config_value("graphiti.request_timeout_seconds", cfg) == 60

    saved = load_config_file(cfg_path)
    assert saved["graphiti"]["enabled"] is True
    assert saved["graphiti"]["request_timeout_seconds"] == 60
