from __future__ import annotations

from memsearch.graphiti.evaluation import DEFAULT_GRAPH_EVALUATION_CASES, GraphEvaluationCase, evaluate_payload


def test_default_cases_cover_current_route_and_negative_controls() -> None:
    cases = {case.name: case for case in DEFAULT_GRAPH_EVALUATION_CASES}

    assert set(cases) >= {
        "relationship-tailscale-current-routing",
        "relationship-mac-mini-current-route",
        "relationship-graphiti-falkordb-mac-mini",
        "negative-nordvpn-meshnet-restart",
        "negative-open-brain-nord-hostnames",
        "negative-stale-mac-mini-ip",
        "negative-retired-graphiti-proxy",
        "relationship-memory-recall-codex-claude",
        "relationship-memory-recall-layers",
        "relationship-memsearch-hybrid-identifiers",
        "relationship-open-brain-advisory-guardrails",
        "negative-codex-forked-memory-recall",
        "relationship-source-freshness-cadence",
        "relationship-manus-card-safety-lane",
        "relationship-linear-source-sync",
        "relationship-secret-scan-gates",
        "negative-index-raw-manus-exports",
        "relationship-platform-capture-shared-memory",
        "relationship-index-chunk-dedup-flow",
        "relationship-config-priority-chain",
        "relationship-watch-compact-loop",
        "relationship-cli-command-roles",
        "negative-api-keys-in-config",
        "negative-milvus-source-of-truth",
        "relationship-installation-backend-profiles",
        "relationship-dimension-mismatch-recovery",
        "relationship-milvus-lite-server-mode",
        "relationship-progressive-disclosure-transcript",
        "relationship-troubleshoot-missing-stale-results",
        "negative-windows-milvus-lite-native",
        "relationship-embedding-evaluation-default",
        "relationship-embedding-model-tradeoffs",
        "relationship-python-api-index-lifecycle",
        "relationship-python-api-isolation-agent-loop",
        "relationship-platform-install-routes",
        "relationship-openclaw-permissions",
        "relationship-codex-installer-changes",
        "relationship-plugin-uninstall-preserves-memory",
        "relationship-opencode-windows-posix",
    }
    assert cases["relationship-mac-mini-current-route"].graph_must_contain == (
        "dom-kamet.tailf78a36.ts.net",
        "100.72.169.59",
    )
    assert cases["relationship-branch-graphiti-falkordb"].graph_must_contain == (
        "dom/mon-316-graphiti-falkordb",
        "Graphiti",
        "FalkorDB",
    )
    assert cases["relationship-tailscale-current-routing"].graph_must_contain == (
        "Tailscale",
        "NordVPN",
        "Meshnet",
        "replaced",
        "not part",
    )
    assert cases["relationship-graphiti-falkordb-mac-mini"].graph_must_contain == (
        "Graphiti",
        "FalkorDB",
        "Mac Mini",
        "Tailscale Serve",
    )
    assert "100.87.225.99" not in cases["relationship-tailscale-current-routing"].graph_must_not_contain
    assert ".nord" not in cases["relationship-graphiti-falkordb-mac-mini"].graph_must_not_contain
    assert "should use .nord" in cases["relationship-mac-mini-current-route"].graph_must_not_contain
    assert "restart NordVPN" in cases["negative-nordvpn-meshnet-restart"].graph_must_not_contain
    assert "historical" in cases["negative-stale-mac-mini-ip"].graph_must_contain
    assert "use the tailnet proxy" in cases["negative-retired-graphiti-proxy"].graph_must_not_contain
    assert cases["relationship-memory-recall-codex-claude"].graph_must_contain == (
        "Codex",
        "main conversation context",
        "Claude Code",
        "forked subagent",
    )
    assert cases["relationship-memory-recall-layers"].graph_must_contain == (
        "L1 search",
        "L2 expand",
        "L3 transcript",
    )
    assert cases["relationship-memsearch-hybrid-identifiers"].graph_must_contain == (
        "BM25",
        "exact identifiers",
        "dense",
    )
    assert cases["relationship-open-brain-advisory-guardrails"].graph_must_contain == (
        "advisory patterns",
        "client_of",
        "works_on",
        "stronger evidence",
    )
    assert "Codex uses a forked subagent" in cases["negative-codex-forked-memory-recall"].graph_must_not_contain
    assert cases["relationship-source-freshness-cadence"].graph_must_contain == (
        "Linear",
        "daily",
        "Manus",
        "weekly",
    )
    assert cases["relationship-manus-card-safety-lane"].graph_must_contain == (
        "Manus",
        "card lane",
        "raw exports",
        "not MemSearch-ready",
    )
    assert cases["relationship-linear-source-sync"].graph_must_contain == (
        "Linear",
        "read-only GraphQL",
        "last_success_at",
        "dry-run previews",
    )
    assert cases["relationship-secret-scan-gates"].graph_must_contain == (
        "scan raw output",
        "scan promoted output",
        "scan cards",
        "index",
    )
    assert "index raw Manus exports" in cases["negative-index-raw-manus-exports"].graph_must_not_contain
    assert cases["relationship-platform-capture-shared-memory"].graph_must_contain == (
        "Claude Code",
        "OpenClaw",
        "OpenCode",
        "Codex CLI",
        "daily markdown",
        "Milvus",
    )
    assert cases["relationship-index-chunk-dedup-flow"].graph_must_contain == (
        "Scanner",
        "Chunker",
        "SHA-256",
        "Milvus",
        "stale chunks",
    )
    assert cases["relationship-config-priority-chain"].graph_must_contain == (
        "built-in defaults",
        "~/.memsearch/config.toml",
        ".memsearch.toml",
        "CLI flags",
    )
    assert cases["relationship-watch-compact-loop"].graph_must_contain == (
        "file watcher",
        "compact",
        "daily markdown",
        "re-index",
    )
    assert cases["relationship-cli-command-roles"].graph_must_contain == (
        "memsearch index",
        "memsearch search",
        "memsearch expand",
        "memsearch compact",
        "memsearch watch",
    )
    assert cases["negative-api-keys-in-config"].graph_must_contain == (
        "API keys",
        "environment variables",
        "never writes API keys to config files",
    )
    assert "store API keys in config" in cases["negative-api-keys-in-config"].graph_must_not_contain
    assert cases["negative-milvus-source-of-truth"].graph_must_contain == (
        "Markdown",
        "source of truth",
        "Milvus",
        "derived index",
    )
    assert "Milvus is the source of truth" in cases["negative-milvus-source-of-truth"].graph_must_not_contain
    assert cases["relationship-installation-backend-profiles"].graph_must_contain == (
        "ONNX",
        "OpenAI",
        "Milvus Lite",
        "Milvus Server",
        "Zilliz Cloud",
        "API key",
    )
    assert "Milvus Lite is recommended to be used with Windows" in cases[
        "relationship-installation-backend-profiles"
    ].graph_must_not_contain
    assert cases["relationship-dimension-mismatch-recovery"].graph_must_contain == (
        "dimension mismatch",
        "embedding provider/model",
        "reset",
        "re-index",
        "Markdown",
    )
    assert cases["relationship-milvus-lite-server-mode"].graph_must_contain == (
        "Milvus Lite",
        "one-time index",
        "Server mode",
        "memsearch watch",
        "Zilliz Cloud",
    )
    assert cases["relationship-progressive-disclosure-transcript"].graph_must_contain == (
        "L1 search",
        "L2 expand",
        "L3 transcript",
        "chunk",
        "full markdown section",
    )
    assert cases["relationship-troubleshoot-missing-stale-results"].graph_must_contain == (
        "memsearch stats",
        "index needs to be rebuilt",
        "stale",
        "too short or vague",
        "embedding provider/model",
    )
    assert cases["negative-windows-milvus-lite-native"].graph_must_contain == (
        "Windows",
        "Milvus Lite",
        "Milvus Server",
        "Zilliz Cloud",
        "WSL2",
    )
    assert "Milvus Lite works natively on Windows" in cases[
        "negative-windows-milvus-lite-native"
    ].graph_must_not_contain
    assert "Milvus Lite is recommended to be used with Windows" in cases[
        "negative-windows-milvus-lite-native"
    ].graph_must_not_contain
    assert cases["relationship-embedding-evaluation-default"].graph_must_contain == (
        "gpahal/bge-m3-onnx-int8",
        "Recall@5",
        "Chinese",
        "no API key",
        "torch",
    )
    assert cases["relationship-embedding-model-tradeoffs"].graph_must_contain == (
        "PyTorch",
        "OpenAI text-embedding-3-small",
        "Ollama",
        "Chinese",
        "Q5 quantization",
    )
    assert cases["relationship-python-api-index-lifecycle"].graph_must_contain == (
        "force=True",
        "content-hash dedup",
        "stale cleanup",
        "deleted files",
    )
    assert cases["relationship-python-api-isolation-agent-loop"].graph_must_contain == (
        "search",
        "saving new memory",
        "index",
        "paths",
        "collection",
        "milvus_uri",
    )
    assert cases["relationship-platform-install-routes"].graph_must_contain == (
        "Claude Code",
        "Marketplace",
        "OpenClaw",
        "ClawHub",
        "OpenCode",
        "npm",
        "Codex",
    )
    assert cases["relationship-openclaw-permissions"].graph_must_contain == (
        "allowConversationAccess",
        "allowPromptInjection",
        "read conversation turns",
        "inject recall context",
    )
    assert cases["relationship-codex-installer-changes"].graph_must_contain == (
        "skills and hooks",
        "~/.agents/skills",
        "~/.codex/hooks.json",
        "hooks to be true",
    )
    assert cases["relationship-plugin-uninstall-preserves-memory"].graph_must_contain == (
        ".memsearch/memory",
        "not delete",
        "Claude Code",
        "OpenClaw",
        "OpenCode",
        "Codex",
    )
    assert cases["relationship-opencode-windows-posix"].graph_must_contain == (
        "OpenCode",
        "native Windows",
        "POSIX shell",
        "WSL2",
        "Git Bash",
        "issue #387",
    )


def test_evaluate_payload_checks_vector_graph_and_negative_controls() -> None:
    case = GraphEvaluationCase(
        name="relationship",
        kind="relationship",
        query="How does Graphiti relate to FalkorDB in MON-316?",
        vector_must_contain=("MON-316",),
        graph_must_contain=("Graphiti", "FalkorDB"),
        graph_must_not_contain=("MON-310",),
    )

    result = evaluate_payload(
        case,
        {
            "vector": [{"heading": "MON-316", "content": "Graphiti FalkorDB plan"}],
            "graph": {
                "facts": [{"fact": "Graphiti is backed by FalkorDB."}],
                "nodes": [{"name": "Graphiti"}],
            },
        },
    )

    assert result["passed"] is True
    assert result["vector_hits"] == ["MON-316"]
    assert result["graph_hits"] == ["Graphiti", "FalkorDB"]
    assert result["graph_unwanted_hits"] == []


def test_evaluate_payload_fails_when_graph_has_unwanted_hits() -> None:
    case = GraphEvaluationCase(
        name="negative",
        kind="negative",
        query="MON-249 homepage performance recovery",
        vector_must_contain=("MON-249",),
        graph_must_not_contain=("Graphiti",),
    )

    result = evaluate_payload(
        case,
        {
            "vector": [{"heading": "MON-249"}],
            "graph": {"facts": [{"fact": "Graphiti memory layer."}], "nodes": []},
        },
    )

    assert result["passed"] is False
    assert result["graph_unwanted_hits"] == ["Graphiti"]
