from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import SourceFile, normalise_machine_name


@dataclass(frozen=True)
class InventoryRule:
    product: str
    relative_glob: str
    source_kind: str = "local"
    is_fallback: bool = False
    status: str = "pending"


HOME_RULES = [
    InventoryRule("claude_code", ".claude/projects/**/*.jsonl"),
    InventoryRule("codex", ".codex/sessions/**/*.jsonl"),
    InventoryRule(
        "claude_desktop_local_agent_jsonl", "Library/Application Support/Claude/local-agent-mode-sessions/**/*.jsonl"
    ),
    InventoryRule(
        "claude_desktop_local_agent_json", "Library/Application Support/Claude/local-agent-mode-sessions/**/*.json"
    ),
    InventoryRule(
        "claude_desktop_code_session",
        "Library/Application Support/Claude/claude-code-sessions/**/*.json",
        status="possible_duplicate_claude_code",
    ),
    InventoryRule("chatgpt_cache", "Library/Application Support/com.openai.chat/**/*", is_fallback=True),
    InventoryRule(
        "manus_indexeddb",
        "Library/Application Support/Manus/IndexedDB/**/*",
        source_kind="indexeddb",
        is_fallback=True,
    ),
    InventoryRule(
        "manus_cache",
        "Library/Application Support/Manus/Cache/**/*",
        source_kind="cache",
        is_fallback=True,
    ),
    InventoryRule("manus_cache", "Library/Application Support/Manus/**/*", is_fallback=True),
    InventoryRule(
        "chatgpt_cache",
        "Library/Application Support/Google/Chrome/Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb/**/*",
        is_fallback=True,
    ),
    InventoryRule(
        "claude_cache",
        "Library/Application Support/Google/Chrome/Default/IndexedDB/https_claude.ai_0.indexeddb.leveldb/**/*",
        is_fallback=True,
    ),
    InventoryRule(
        "manus_indexeddb",
        "Library/Application Support/Google/Chrome/Default/IndexedDB/https_manus.im_0.indexeddb.leveldb/**/*",
        source_kind="indexeddb",
        is_fallback=True,
    ),
]

EXPORT_RULES = [
    InventoryRule("chatgpt_export", ".local/chat-exports/**/conversations.json", source_kind="export"),
    InventoryRule("chatgpt_export", ".local/chat-exports/**/chat.html", source_kind="export"),
    InventoryRule("claude_export", ".local/chat-exports/**/claude*.json", source_kind="export"),
    InventoryRule("claude_export", ".local/chat-exports/**/conversations*.json", source_kind="export"),
]


def collect_inventory(
    *,
    home: str | Path,
    machine: str,
    repo_root: str | Path | None = None,
) -> list[SourceFile]:
    """Collect candidate transcript/export files without modifying sources."""
    home_path = Path(home).expanduser()
    machine_name = normalise_machine_name(machine)
    files: list[SourceFile] = []
    seen: set[Path] = set()

    for rule in HOME_RULES:
        _collect_rule(home_path, rule, machine_name, files, seen)

    if repo_root is not None:
        repo_path = Path(repo_root).expanduser()
        for rule in EXPORT_RULES:
            _collect_rule(repo_path, rule, machine_name, files, seen)

    return sorted(files, key=lambda f: (f.product, str(f.path)))


def _collect_rule(root: Path, rule: InventoryRule, machine: str, files: list[SourceFile], seen: set[Path]) -> None:
    if not root.exists():
        return
    for path in root.glob(rule.relative_glob):
        if not path.is_file():
            continue
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(
            SourceFile.from_path(
                resolved,
                product=rule.product,
                machine=machine,
                source_kind=rule.source_kind,
                is_fallback=rule.is_fallback,
                status=rule.status,
            )
        )
