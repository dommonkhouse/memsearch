"""Small evaluation helpers for opt-in Graphiti recall."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphEvaluationCase:
    name: str
    kind: str
    query: str
    vector_must_contain: tuple[str, ...] = ()
    graph_must_contain: tuple[str, ...] = ()
    graph_must_not_contain: tuple[str, ...] = ()


DEFAULT_GRAPH_EVALUATION_CASES = (
    GraphEvaluationCase(
        name="exact-mon-316",
        kind="exact",
        query="MON-316",
        vector_must_contain=("MON-316",),
    ),
    GraphEvaluationCase(
        name="exact-mon-259",
        kind="exact",
        query="MON-259",
        vector_must_contain=("MON-259",),
    ),
    GraphEvaluationCase(
        name="exact-branch",
        kind="exact",
        query="dom/mon-316-graphiti-falkordb",
        vector_must_contain=("dom/mon-316-graphiti-falkordb",),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-falkordb-mon316",
        kind="relationship",
        query="How does Graphiti relate to FalkorDB and Tailscale Serve in MON-316?",
        vector_must_contain=("MON-316",),
        graph_must_contain=("Graphiti", "FalkorDB", "Tailscale Serve"),
    ),
    GraphEvaluationCase(
        name="relationship-branch-graphiti-falkordb",
        kind="relationship",
        query="How is dom/mon-316-graphiti-falkordb connected to Graphiti and FalkorDB?",
        vector_must_contain=("dom/mon-316-graphiti-falkordb",),
        graph_must_contain=("dom/mon-316-graphiti-falkordb", "Graphiti", "FalkorDB"),
    ),
    GraphEvaluationCase(
        name="relationship-tailscale-current-routing",
        kind="relationship",
        query="Is NordVPN still used or is this Tailscale only?",
        graph_must_contain=("Tailscale", "NordVPN", "Meshnet", "replaced", "not part"),
        graph_must_not_contain=(
            "restart NordVPN",
            "restart Meshnet",
            "should use NordVPN",
            "should use Meshnet",
            "should use .nord",
            "use .nord",
            "use 100.87.225.99",
            "100.87.225.99 is current",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-mac-mini-current-route",
        kind="relationship",
        query="What host should I use for the Mac Mini now NordVPN Meshnet is retired?",
        graph_must_contain=("dom-kamet.tailf78a36.ts.net", "100.72.169.59"),
        graph_must_not_contain=("should use .nord", "use 100.87.225.99", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-falkordb-mac-mini",
        kind="relationship",
        query="How does Graphiti reach FalkorDB on the Mac Mini through Tailscale Serve?",
        graph_must_contain=("Graphiti", "FalkorDB", "Mac Mini", "Tailscale Serve"),
        graph_must_not_contain=("should use .nord", "use 100.87.225.99", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="relationship-memory-recall-codex-claude",
        kind="relationship",
        query="How does memory recall differ between Codex and Claude Code?",
        graph_must_contain=("Codex", "main conversation context", "Claude Code", "forked subagent"),
        graph_must_not_contain=("Codex uses a forked subagent",),
    ),
    GraphEvaluationCase(
        name="relationship-memory-recall-layers",
        kind="relationship",
        query="What are the L1 L2 and L3 layers in MemSearch memory recall?",
        graph_must_contain=("L1 search", "L2 expand", "L3 transcript"),
    ),
    GraphEvaluationCase(
        name="relationship-memsearch-hybrid-identifiers",
        kind="relationship",
        query="Why does MemSearch help with exact identifiers compared with dense-only memory search?",
        graph_must_contain=("BM25", "exact identifiers", "dense"),
    ),
    GraphEvaluationCase(
        name="relationship-open-brain-advisory-guardrails",
        kind="relationship",
        query="What relationship edges should Open Brain avoid inferring from advisory conversations?",
        graph_must_contain=("advisory patterns", "client_of", "works_on", "stronger evidence"),
        graph_must_not_contain=("Dominic works_on salon owners", "Dominic client_of salon owners"),
    ),
    GraphEvaluationCase(
        name="relationship-source-freshness-cadence",
        kind="relationship",
        query="What is the source freshness cadence for Linear and Manus?",
        graph_must_contain=("Linear", "daily", "Manus", "weekly"),
    ),
    GraphEvaluationCase(
        name="relationship-manus-card-safety-lane",
        kind="relationship",
        query="Why are Manus cards the practical MemSearch indexing source instead of raw exports?",
        graph_must_contain=("Manus", "card lane", "raw exports", "not MemSearch-ready"),
        graph_must_not_contain=("index raw Manus exports",),
    ),
    GraphEvaluationCase(
        name="relationship-linear-source-sync",
        kind="relationship",
        query="How does Linear source sync work for MemSearch freshness?",
        graph_must_contain=("Linear", "read-only GraphQL", "last_success_at", "dry-run previews"),
    ),
    GraphEvaluationCase(
        name="relationship-secret-scan-gates",
        kind="relationship",
        query="What secret scan gates protect Manus source sync before indexing?",
        graph_must_contain=("scan raw output", "scan promoted output", "scan cards", "index"),
    ),
    GraphEvaluationCase(
        name="relationship-platform-capture-shared-memory",
        kind="relationship",
        query="How do MemSearch platform plugins capture memories across Claude Code Codex OpenClaw and OpenCode?",
        graph_must_contain=("Claude Code", "OpenClaw", "OpenCode", "Codex CLI", "daily markdown", "Milvus"),
    ),
    GraphEvaluationCase(
        name="relationship-index-chunk-dedup-flow",
        kind="relationship",
        query="How does MemSearch chunk markdown and deduplicate chunks before indexing?",
        graph_must_contain=("Scanner", "Chunker", "SHA-256", "Milvus", "stale chunks"),
    ),
    GraphEvaluationCase(
        name="relationship-config-priority-chain",
        kind="relationship",
        query="How does MemSearch configuration choose between defaults global project config and CLI flags?",
        graph_must_contain=("built-in defaults", "~/.memsearch/config.toml", ".memsearch.toml", "CLI flags"),
    ),
    GraphEvaluationCase(
        name="relationship-watch-compact-loop",
        kind="relationship",
        query="How does the watcher compact memory and re-index markdown?",
        graph_must_contain=("file watcher", "compact", "daily markdown", "re-index"),
    ),
    GraphEvaluationCase(
        name="relationship-cli-command-roles",
        kind="relationship",
        query="How do CLI commands relate to indexing search expand compact and watch?",
        graph_must_contain=(
            "memsearch index",
            "memsearch search",
            "memsearch expand",
            "memsearch compact",
            "memsearch watch",
        ),
    ),
    GraphEvaluationCase(
        name="negative-api-keys-in-config",
        kind="negative",
        query="Does MemSearch write API keys into config files?",
        graph_must_contain=("API keys", "environment variables", "never writes API keys to config files"),
        graph_must_not_contain=("write API keys to config", "store API keys in config"),
    ),
    GraphEvaluationCase(
        name="negative-milvus-source-of-truth",
        kind="negative",
        query="Is Milvus the source of truth for MemSearch memories?",
        graph_must_contain=("Markdown", "source of truth", "Milvus", "derived index"),
        graph_must_not_contain=("Milvus is the source of truth",),
    ),
    GraphEvaluationCase(
        name="relationship-installation-backend-profiles",
        kind="relationship",
        query="How do MemSearch installation profiles choose local embeddings OpenAI-compatible embeddings Milvus Lite Server and Zilliz?",
        graph_must_contain=("ONNX", "OpenAI", "Milvus Lite", "Milvus Server", "Zilliz Cloud", "API key"),
        graph_must_not_contain=("Milvus Lite is recommended to be used with Windows",),
    ),
    GraphEvaluationCase(
        name="relationship-dimension-mismatch-recovery",
        kind="relationship",
        query="How should MemSearch recover from dimension mismatch or changed embedding model?",
        graph_must_contain=("dimension mismatch", "embedding provider/model", "reset", "re-index", "Markdown"),
    ),
    GraphEvaluationCase(
        name="relationship-milvus-lite-server-mode",
        kind="relationship",
        query="How does the Codex plugin handle Milvus Lite lock mode versus Server mode?",
        graph_must_contain=("Milvus Lite", "one-time index", "Server mode", "memsearch watch", "Zilliz Cloud"),
    ),
    GraphEvaluationCase(
        name="relationship-progressive-disclosure-transcript",
        kind="relationship",
        query="How do MemSearch progressive disclosure commands search expand transcript relate to chunks and source files?",
        graph_must_contain=("L1 search", "L2 expand", "L3 transcript", "chunk", "full markdown section"),
    ),
    GraphEvaluationCase(
        name="relationship-troubleshoot-missing-stale-results",
        kind="relationship",
        query="What should MemSearch do when search results are missing stale or too vague?",
        graph_must_contain=(
            "memsearch stats",
            "index needs to be rebuilt",
            "stale",
            "too short or vague",
            "embedding provider/model",
        ),
    ),
    GraphEvaluationCase(
        name="negative-windows-milvus-lite-native",
        kind="negative",
        query="Should Windows use Milvus Lite directly for MemSearch?",
        graph_must_contain=("Windows", "Milvus Lite", "Milvus Server", "Zilliz Cloud", "WSL2"),
        graph_must_not_contain=(
            "Milvus Lite works natively on Windows",
            "Milvus Lite is recommended to be used with Windows",
            "use native Milvus Lite on Windows",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-embedding-evaluation-default",
        kind="relationship",
        query="Why did MemSearch choose ONNX bge-m3 int8 as the Claude Code plugin default?",
        graph_must_contain=(
            "gpahal/bge-m3-onnx-int8",
            "Recall@5",
            "Chinese",
            "no API key",
            "torch",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-embedding-model-tradeoffs",
        kind="relationship",
        query="How do ONNX bge-m3 int8 PyTorch OpenAI small and Ollama relate in MemSearch embedding evaluation?",
        graph_must_contain=("PyTorch", "OpenAI text-embedding-3-small", "Ollama", "Chinese", "Q5 quantization"),
    ),
    GraphEvaluationCase(
        name="relationship-python-api-index-lifecycle",
        kind="relationship",
        query="How does the Python API handle force re-index stale cleanup deleted content and content-hash dedup?",
        graph_must_contain=("force=True", "content-hash dedup", "stale cleanup", "deleted files"),
    ),
    GraphEvaluationCase(
        name="relationship-python-api-isolation-agent-loop",
        kind="relationship",
        query="How do MemSearch Python API agent loops and per-user isolation relate to paths collections and milvus_uri?",
        graph_must_contain=("search", "saving new memory", "index", "paths", "collection", "milvus_uri"),
    ),
    GraphEvaluationCase(
        name="relationship-platform-install-routes",
        kind="relationship",
        query="How do MemSearch platform installs differ across Claude Code OpenClaw OpenCode and Codex CLI?",
        graph_must_contain=("Claude Code", "Marketplace", "OpenClaw", "ClawHub", "OpenCode", "npm", "Codex"),
    ),
    GraphEvaluationCase(
        name="relationship-openclaw-permissions",
        kind="relationship",
        query="What permissions does the OpenClaw MemSearch plugin require and why?",
        graph_must_contain=(
            "allowConversationAccess",
            "allowPromptInjection",
            "read conversation turns",
            "inject recall context",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-codex-installer-changes",
        kind="relationship",
        query="What does the Codex MemSearch installer change in hooks config and skills?",
        graph_must_contain=("skills and hooks", "~/.agents/skills", "~/.codex/hooks.json", "hooks to be true"),
    ),
    GraphEvaluationCase(
        name="relationship-plugin-uninstall-preserves-memory",
        kind="relationship",
        query="How do MemSearch plugin uninstall steps preserve memory files across Claude Code OpenClaw OpenCode and Codex?",
        graph_must_contain=(".memsearch/memory", "not delete", "Claude Code", "OpenClaw", "OpenCode", "Codex"),
    ),
    GraphEvaluationCase(
        name="relationship-opencode-windows-posix",
        kind="relationship",
        query="How do OpenCode native Windows POSIX shell WSL2 and Git Bash relate to MemSearch plugin install?",
        graph_must_contain=("OpenCode", "native Windows", "POSIX shell", "WSL2", "Git Bash", "issue #387"),
    ),
    GraphEvaluationCase(
        name="relationship-platform-memory-execution-contexts",
        kind="relationship",
        query="Which MemSearch platforms use forked subagent main context registerTool or tool API for memory recall?",
        graph_must_contain=(
            "Claude Code",
            "forked subagent",
            "Codex",
            "main context",
            "OpenClaw",
            "registerTool",
            "OpenCode",
            "tool() API",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-platform-memory-manual-triggers",
        kind="relationship",
        query="How do manual MemSearch memory recall triggers differ between Claude Code Codex OpenClaw and OpenCode?",
        graph_must_contain=("Claude Code", "/memory-recall", "Codex", "$memory-recall", "OpenClaw", "OpenCode"),
    ),
    GraphEvaluationCase(
        name="relationship-platform-memory-transcript-sources",
        kind="relationship",
        query="How do memory transcript sources differ across Claude Code Codex OpenClaw and OpenCode?",
        graph_must_contain=(
            "Claude Code",
            "JSONL",
            "Codex",
            "parse-rollout.sh",
            "OpenClaw",
            "parse-transcript.sh",
            "OpenCode",
            "SQLite",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-opencode-openclaw-transcript-difference",
        kind="relationship",
        query="How do OpenCode memory_transcript and OpenClaw memory_transcript differ?",
        graph_must_contain=("OpenCode", "SQLite", "session_id", "turn_id", "OpenClaw", "transcript_path", "JSONL"),
    ),
    GraphEvaluationCase(
        name="relationship-source-sync-linear-indexing",
        kind="relationship",
        query="How does source-sync linear use last_success_at dry-run and optional indexing?",
        graph_must_contain=(
            "Linear",
            "last_success_at",
            "dry-run previews",
            "--index",
            "memsearch_chunks",
            "scan_path_for_secrets",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-manus-weekly-safety-sequence",
        kind="relationship",
        query="What gates happen before Manus cards can be indexed into MemSearch?",
        graph_must_contain=(
            "verifying the run",
            "scanning the raw run",
            "promoting sanitised Markdown",
            "Scanning the promoted output",
            "Generating cards",
            "scanning the cards",
            "--index",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-scheduler-render-approval-gate",
        kind="relationship",
        query="What does scheduler-render create and why does it not install LaunchAgents automatically?",
        graph_must_contain=(
            "scheduler-render",
            "com.memsearch.daily-linear-sync.plist",
            "com.memsearch.weekly-manus-sync.plist",
            ".local/source-sync-logs",
            "approval",
            "launchctl",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-source-freshness-report-proof",
        kind="relationship",
        query="What does source-freshness report and how do proof searches work?",
        graph_must_contain=(
            "state presence",
            "last success",
            "last failure",
            "generated Markdown card counts",
            "next expected run",
            "proof-search",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-alternatives-fit",
        kind="relationship",
        query="When should I choose memsearch instead of Claude Code native memory mem0 Letta or qmd?",
        graph_must_contain=(
            "memsearch",
            "Claude Code native",
            "mem0",
            "Letta",
            "qmd",
            "coding CLI",
            "local markdown search engine",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-markdown-source-of-truth-design",
        kind="relationship",
        query="Why does memsearch treat Markdown as source of truth and Milvus as a derived index?",
        graph_must_contain=(
            "Markdown",
            "source of truth",
            "Milvus",
            "derived index",
            "rebuild",
            "vendor lock-in",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-user-workflows-progressive-recall",
        kind="relationship",
        query="What user workflows does memsearch support and how does progressive recall work?",
        graph_must_contain=(
            "debugging threads",
            "decision rationale",
            "feature history",
            "code archaeology",
            "L1",
            "L2",
            "L3",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-audience-routes-users-developers",
        kind="relationship",
        query="How does memsearch serve agent users and agent developers differently?",
        graph_must_contain=(
            "Agent Users",
            "install a plugin",
            "Agent Developers",
            "CLI",
            "Python API",
            "zero commands",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plugin-summarization-routing",
        kind="relationship",
        query="How do memsearch plugin summarization routing settings relate to native providers llm.providers and llm.model?",
        graph_must_contain=(
            "plugin-specific",
            "native",
            "llm.providers",
            "summarize.provider",
            "llm.model",
            "do not revert",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-platform-plugin-shared-architecture",
        kind="relationship",
        query="How do memsearch platform plugins share capture recall transcript and install architecture?",
        graph_must_contain=(
            "platform plugins",
            "Plugin capture",
            "Plugin recall",
            "L3 transcript",
            "standard markdown",
            "Codex CLI",
            "installer script",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-agent-framework-integrations",
        kind="relationship",
        query="How does memsearch integrate with LangChain LangGraph LlamaIndex and CrewAI?",
        graph_must_contain=(
            "LangChain",
            "BaseRetriever",
            "LangGraph",
            "ReAct agent",
            "LlamaIndex",
            "NodeWithScore",
            "CrewAI",
            "tool",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-cross-platform-sharing-isolation",
        kind="relationship",
        query="How does memsearch share memories across platforms while isolating different projects?",
        graph_must_contain=(
            "same project directory",
            "same collection name",
            "different project directories",
            "standard markdown",
            "shared memories",
            "isolated",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-zero-config-backend-choice",
        kind="relationship",
        query="How should I choose between zero-config local setup Milvus Lite Milvus Server and Zilliz Cloud?",
        graph_must_contain=(
            "local embeddings",
            "no API key",
            "Milvus Lite",
            "Milvus Server",
            "Zilliz Cloud",
            "production",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-agent-loop-recall-think-remember",
        kind="relationship",
        query="How does a memsearch agent loop recall think remember and keep daily markdown indexed?",
        graph_must_contain=(
            "Recall",
            "Think",
            "Remember",
            "daily markdown",
            "LLM",
            "re-index",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-python-api-per-user-isolation",
        kind="relationship",
        query="How does the Python API isolate different users with paths collections and milvus_uri?",
        graph_must_contain=(
            "per-user isolation",
            "paths",
            "collection",
            "milvus_uri",
            "separate database",
            "never see each other's data",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-troubleshooting-reset-rebuild",
        kind="relationship",
        query="When search is stale missing irrelevant or dimension mismatch happens how should memsearch reset and rebuild?",
        graph_must_contain=(
            "memsearch stats",
            "memsearch reset --yes",
            "memsearch index",
            "source markdown",
            "dimension mismatch",
            "embedding provider/model",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-progressive-disclosure-anchor-bridge",
        kind="relationship",
        query="How do session anchors transcript path and original conversation connect L1 search L2 expand and L3 transcript?",
        graph_must_contain=(
            "L1 search",
            "L2 expand",
            "L3 transcript",
            "session anchors",
            "transcript path",
            "original conversation",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-derived-index-rebuild-safety",
        kind="relationship",
        query="Why is rebuilding safe with Markdown source of truth Milvus derived index and content-hash dedup?",
        graph_must_contain=(
            "Markdown",
            "source of truth",
            "Milvus",
            "derived index",
            "content-hash dedup",
            "rebuild",
        ),
        graph_must_not_contain=("Milvus is the source of truth",),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-sidecar-cli-routing",
        kind="relationship",
        query="How do graph-status graph-index graph-search and search --include-graph relate to the optional Graphiti sidecar?",
        graph_must_contain=(
            "graph-status",
            "graph-index",
            "graph-search",
            "include-graph",
            "Graphiti",
            "sidecar",
            "Markdown remains the source of truth",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-source-sync-approval-boundaries",
        kind="relationship",
        query="What approval and safety boundaries govern Linear and Manus source sync indexing?",
        graph_must_contain=(
            "Linear",
            "Manus",
            "dry-run",
            "secret scans",
            "approval",
            "canonical indexing",
        ),
        graph_must_not_contain=("perform silent full export", "index raw event logs directly"),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-mcp-route-host-header",
        kind="relationship",
        query="What Graphiti MCP endpoint Host header DNS-rebinding and trailing slash rules should clients use?",
        graph_must_contain=(
            "http://dom-kamet.tailf78a36.ts.net:8018/mcp",
            "Host header",
            "127.0.0.1:18018",
            "trailing slash",
            "DNS-rebinding",
        ),
        graph_must_not_contain=("should use /mcp/ with a trailing slash",),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-runtime-isolation",
        kind="relationship",
        query="How is the Graphiti FalkorDB runtime isolated from Milvus using dedicated Colima profile graphiti-mon316 on the Mac Mini?",
        graph_must_contain=(
            "Mac Mini",
            "dedicated Colima profile",
            "graphiti-mon316",
            "/Volumes/SSD/graphiti-mon316",
            "FalkorDB",
            "Milvus",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-login-supervision-boundary",
        kind="relationship",
        query="Is Graphiti reboot-proof operation blocked by autoLoginUser_missing kcpassword_missing sudo_unavailable or supervised by LaunchAgent?",
        graph_must_contain=(
            "LaunchAgent",
            "reboot-proof operation",
            "autoLoginUser_missing",
            "kcpassword_missing",
            "sudo_unavailable",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-graphiti-rollback-boundary",
        kind="relationship",
        query="Graphiti rollback stop Graphiti Compose preserve Milvus manifest",
        graph_must_contain=(
            "Graphiti rollback",
            "Markdown memory files",
            "Milvus",
            "Graphiti manifest",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-platform-cold-start-injection",
        kind="relationship",
        query="How do Claude Code Codex OpenClaw and OpenCode inject recent MemSearch memories at cold start?",
        graph_must_contain=(
            "Claude Code",
            "SessionStart",
            "Codex",
            "memory file count and date range",
            "OpenClaw",
            "before_agent_start",
            "OpenCode",
            "system.transform",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-platform-capture-isolation",
        kind="relationship",
        query="How do platform capture summarisers avoid recursion across Claude Code Codex OpenClaw and OpenCode?",
        graph_must_contain=(
            "Claude Code",
            "stop_hook_active",
            "Codex",
            "features.hooks=false",
            "OpenClaw",
            "MEMSEARCH_NO_WATCH",
            "OpenCode",
            "XDG_CONFIG_HOME",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-platform-watch-index-modes",
        kind="relationship",
        query="How do Claude Code Codex OpenClaw and OpenCode choose memsearch watch one-time index background index or capture-daemon.py indexing?",
        graph_must_contain=(
            "Claude Code",
            "memsearch watch",
            "Codex",
            "Milvus Lite",
            "one-time index",
            "OpenClaw",
            "background",
            "OpenCode",
            "capture-daemon.py",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-opencode-sidecar-boundary",
        kind="relationship",
        query="For OpenCode, what is source of truth between SQLite markdown memory and opencode-turns sidecar state?",
        graph_must_contain=(
            "OpenCode SQLite",
            "source of truth",
            "markdown",
            "opencode-turns.db",
            "derived capture state",
            "session+turn anchor",
        ),
        graph_must_not_contain=("opencode-turns.db is the source of truth",),
    ),
    GraphEvaluationCase(
        name="relationship-claude-status-api-key-troubleshooting",
        kind="relationship",
        query=(
            "When Claude Code MemSearch has a missing API key, what keeps writing .md files "
            "and what semantic search or indexing path is disabled?"
        ),
        graph_must_contain=(
            "Claude Code",
            "API key",
            "memory recording",
            ".md files",
            "semantic search",
            "indexing",
            "ONNX",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-claude-watch-recovery-lite-boundary",
        kind="relationship",
        query="How should Claude Code troubleshoot memsearch watch PID recovery and Milvus Lite one-time indexing?",
        graph_must_contain=(
            ".memsearch/.watch.pid",
            "memsearch watch",
            'pgrep -f "memsearch watch"',
            "Milvus Lite",
            "one-time index",
            "Milvus Server",
            "Zilliz Cloud",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-codex-recall-expand-fallback",
        kind="relationship",
        query=(
            "How does Codex L2 use memsearch expand first, then direct file read fallback "
            "with source, start_line, end_line anchors?"
        ),
        graph_must_contain=(
            "Codex",
            "main context",
            "memsearch expand",
            "direct file read",
            "source",
            "start_line",
            "end_line",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-memory-tools-comparison",
        kind="relationship",
        query=(
            "How do OpenClaw and OpenCode MemSearch's three tools compare with "
            "dense-only memory-core, memory-lancedb, and opencode-mem?"
        ),
        graph_must_contain=(
            "OpenClaw",
            "OpenCode",
            "memory_search",
            "memory_get",
            "memory_transcript",
            "memory-core",
            "memory-lancedb",
            "opencode-mem",
            "dense-only",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-graphiti-sidecar-boundaries",
        kind="relationship",
        query="Graphiti optional derived Markdown canonical Milvus explicit CLI prompt injection",
        graph_must_contain=(
            "Graphiti",
            "optional derived",
            "Markdown",
            "canonical",
            "Milvus",
            "explicit CLI",
            "prompt injection",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-kuzu-deferred",
        kind="relationship",
        query="Kuzu deferred archived crash FalkorDB pilot",
        graph_must_contain=(
            "Kuzu",
            "deferred",
            "archived",
            "crash",
            "FalkorDB",
            "pilot",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-capped-ingest-rollback",
        kind="relationship",
        query="Graphiti capped ingest dry-run rollback manifest .memsearch/memory",
        graph_must_contain=(
            "Graphiti",
            "dry-run",
            "rollback",
            "Graphiti manifest",
            ".memsearch/memory",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-chat-backfill-source-normalisation",
        kind="relationship",
        query="chat backfill canonical markdown memsearch index Milvus derived index",
        graph_must_contain=(
            "Markdown",
            "memsearch index",
            "Milvus",
            "derived index",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-manus-three-lane-recall",
        kind="relationship",
        query="Manus card lane practical MemSearch indexing source raw exports",
        graph_must_contain=(
            "Manus card lane",
            "practical MemSearch indexing source",
            "Manus raw exports",
            "not MemSearch-ready",
            "full cleaned transcripts",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-plan-source-freshness-scheduling",
        kind="relationship",
        query="Linear daily Manus weekly dry-run changed tasks silent full export source freshness",
        graph_must_contain=(
            "Linear source sync",
            "Manus source sync",
            "weekly run",
            "dry-run previews",
            "changed tasks only",
            "silent full export",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-batch019-mini-ssd-isolation",
        kind="relationship",
        query="Mac Mini Graphiti SSD Colima profile Milvus isolation runtime state",
        graph_must_contain=(
            "Mac Mini",
            "/Volumes/SSD/graphiti-mon316",
            "graphiti-mon316",
            "COLIMA_HOME",
            "Milvus",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-batch019-mini-mcp-routing",
        kind="relationship",
        query="Graphiti MCP Tailnet Tailscale Serve Host header DNS rebinding no trailing slash",
        graph_must_contain=(
            "Tailscale Serve",
            "http://dom-kamet.tailf78a36.ts.net:8018/mcp",
            "127.0.0.1:18018",
            "DNS-rebinding",
            "trailing slash",
        ),
        graph_must_not_contain=("should use /mcp/ with a trailing slash",),
    ),
    GraphEvaluationCase(
        name="relationship-batch019-mini-login-session-boundary",
        kind="relationship",
        query="Graphiti LaunchAgent login supervision autoLoginUser_missing kcpassword_missing sudo_unavailable reboot-proof",
        graph_must_contain=(
            "LaunchAgent",
            "reboot-proof",
            "autoLoginUser_missing",
            "kcpassword_missing",
            "sudo_unavailable",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-batch019-mini-rollback-safety",
        kind="relationship",
        query="Graphiti rollback stop Graphiti Compose preserve Milvus manifest",
        graph_must_contain=(
            "Graphiti rollback",
            "Markdown memory files",
            "Milvus",
            "Graphiti manifest",
        ),
    ),
    GraphEvaluationCase(
        name="relationship-batch020-macbook-pilot-historical",
        kind="relationship",
        query="MacBook Graphiti pilot historical current Mac Mini Tailscale Serve route group manifest",
        graph_must_contain=(
            "historical",
            "Mac Mini",
            "Tailscale Serve",
            "graphiti-falkordb.md",
        ),
        graph_must_not_contain=("127.0.0.1:8018 is current", "ms_memsearch_ae2d4f9b is current"),
    ),
    GraphEvaluationCase(
        name="relationship-batch021-platform-index-boundaries",
        kind="relationship",
        query="Claude Code Codex OpenClaw OpenCode platform index capture recall cold-start boundaries",
        graph_must_contain=(
            "Claude Code",
            "forked subagent",
            "Codex",
            "OpenClaw",
            "agent_end",
            "OpenCode",
            "SQLite daemon",
        ),
    ),
    GraphEvaluationCase(
        name="negative-mon-249-performance",
        kind="negative",
        query="MON-249 homepage performance recovery",
        graph_must_not_contain=("Graphiti", "FalkorDB"),
    ),
    GraphEvaluationCase(
        name="negative-generic-relationship-word",
        kind="negative",
        query="What is the relationship between MON-249 and homepage performance?",
        graph_must_not_contain=("Relationship Type",),
    ),
    GraphEvaluationCase(
        name="negative-nordvpn-meshnet-restart",
        kind="negative",
        query="Should I restart NordVPN Meshnet to fix MemSearch?",
        graph_must_not_contain=(
            "restart NordVPN",
            "restart Meshnet",
            "should use .nord",
            "use 100.87.225.99",
            "100.87.225.99 is current",
        ),
    ),
    GraphEvaluationCase(
        name="negative-open-brain-nord-hostnames",
        kind="negative",
        query="Should I use .nord hostnames for Open Brain now?",
        graph_must_contain=("not use .nord",),
        graph_must_not_contain=("should use .nord", "dom-kamet.nord is current", "100.87.225.99 is current"),
    ),
    GraphEvaluationCase(
        name="negative-stale-mac-mini-ip",
        kind="negative",
        query="Is 100.87.225.99 the current Mac Mini route?",
        graph_must_contain=("100.87.225.99", "historical", "stale"),
        graph_must_not_contain=("100.87.225.99 is current", "uses 100.87.225.99"),
    ),
    GraphEvaluationCase(
        name="negative-retired-graphiti-proxy",
        kind="negative",
        query="Should Graphiti tailnet access use the retired tailnet proxy LaunchAgent or old SSH-forward route?",
        graph_must_not_contain=("use the tailnet proxy", "use SSH-forward", "use ssh forward", "should use .nord"),
    ),
    GraphEvaluationCase(
        name="negative-codex-forked-memory-recall",
        kind="negative",
        query="Does Codex memory-recall run inside a forked subagent?",
        graph_must_contain=("Codex", "main conversation context"),
        graph_must_not_contain=("Codex uses a forked subagent", "Codex memory-recall uses a forked subagent"),
    ),
    GraphEvaluationCase(
        name="negative-index-raw-manus-exports",
        kind="negative",
        query="Should MemSearch index raw Manus exports directly?",
        graph_must_contain=("Raw Manus exports", "must not be indexed"),
        graph_must_not_contain=("index raw Manus exports", "raw Manus exports should be indexed"),
    ),
)


def evaluate_payload(case: GraphEvaluationCase, payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one vector+graph payload against a lightweight control case."""
    vector_text = _stringify(payload.get("vector", []))
    graph_text = _stringify_graph(payload.get("graph", {}))
    vector_hits = _hits(vector_text, case.vector_must_contain)
    graph_hits = _hits(graph_text, case.graph_must_contain)
    graph_unwanted_hits = _hits(graph_text, case.graph_must_not_contain)
    passed = (
        len(vector_hits) == len(case.vector_must_contain)
        and len(graph_hits) == len(case.graph_must_contain)
        and not graph_unwanted_hits
        and not payload.get("graph_error")
    )
    return {
        "name": case.name,
        "kind": case.kind,
        "query": case.query,
        "passed": passed,
        "vector_hits": vector_hits,
        "graph_hits": graph_hits,
        "graph_unwanted_hits": graph_unwanted_hits,
        "graph_fact_count": len(payload.get("graph", {}).get("facts", [])),
        "graph_node_count": len(payload.get("graph", {}).get("nodes", [])),
        "graph_error": payload.get("graph_error"),
    }


def _hits(text: str, needles: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [needle for needle in needles if needle.casefold() in lowered]


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _stringify_graph(value: Any) -> str:
    if not isinstance(value, dict):
        return _stringify(value)
    facts = value.get("facts", [])
    nodes = value.get("nodes", [])
    parts: list[str] = []
    if isinstance(facts, list):
        parts.extend(str(fact.get("fact", "")) for fact in facts if isinstance(fact, dict))
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                parts.append(str(node.get("name", "")))
                parts.append(str(node.get("summary", "")))
    return " ".join(parts)
