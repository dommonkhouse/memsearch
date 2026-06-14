from __future__ import annotations

from pathlib import Path

import yaml


def test_graphiti_compose_has_restart_policy_and_persistent_falkordb_volume():
    compose = yaml.safe_load(Path("deploy/graphiti/docker-compose.yml").read_text())
    services = compose["services"]

    assert services["falkordb"]["restart"] == "unless-stopped"
    assert services["graphiti-mcp"]["restart"] == "unless-stopped"
    assert "falkordb_data:/var/lib/falkordb/data" in services["falkordb"]["volumes"]
    assert "6379:6379" not in str(services["falkordb"].get("ports", []))
