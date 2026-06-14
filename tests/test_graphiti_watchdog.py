from __future__ import annotations

import pytest

from memsearch.graphiti.watchdog import WatchdogCheck, WatchdogDecision, decide_recovery, run_recovery_commands


def test_watchdog_noops_when_all_checks_pass():
    checks = [
        WatchdogCheck("local_health", True, "ok"),
        WatchdogCheck("tailnet_health", True, "ok"),
        WatchdogCheck("colima_graphiti_mon316", True, "running"),
        WatchdogCheck("compose", True, "ok"),
        WatchdogCheck("tailscale_serve", True, "ok"),
        WatchdogCheck("ssd_space", True, "ok"),
    ]

    assert decide_recovery(checks) == WatchdogDecision(action="noop", reason="all checks passed")


def test_watchdog_restarts_graphiti_only_for_failed_health():
    checks = [
        WatchdogCheck("local_health", False, "connection refused"),
        WatchdogCheck("compose", True, "containers running"),
        WatchdogCheck("milvus", True, "healthy"),
    ]

    decision = decide_recovery(checks)

    assert decision.action == "restart_graphiti"
    assert "milvus" not in decision.commands
    assert any("start-graphiti-mon316.sh" in command for command in decision.commands)


def test_watchdog_reapplies_tailscale_serve_when_forward_missing():
    checks = [WatchdogCheck("tailscale_serve", False, "missing tcp 8018")]

    decision = decide_recovery(checks)

    assert decision.action == "repair_tailscale_serve"
    assert decision.commands == ("tailscale serve --bg --tcp=8018 tcp://127.0.0.1:18018",)


def test_watchdog_recovery_refuses_milvus_command():
    with pytest.raises(ValueError, match="milvus"):
        run_recovery_commands(("docker restart milvus",))
