# Batch 007 source review

Reviewed on 2026-06-13 for MON-316 capped Graphiti platform installation, permissions, update, uninstall, and Windows/POSIX recall tuning.

## Source safety decisions

- `docs/platforms/claude-code/installation.md`: safe to distil, unsafe for direct ingestion. It contains command snippets and lifecycle instructions; Batch 007 only needs install/update/uninstall relationships.
- `docs/platforms/openclaw/installation.md`: safe to distil, unsafe for direct ingestion. It contains command snippets and settings; Batch 007 only needs permission and install/update relationships.
- `docs/platforms/opencode/installation.md`: safe to distil, unsafe for direct ingestion. It contains warning and uninstall commands; Batch 007 only needs Windows/POSIX and install/update/uninstall relationships.
- `docs/platforms/codex/installation.md`: safe to distil, unsafe for direct ingestion. It contains an uninstall script touching user config; Batch 007 only needs installer, full-access, update, and preservation relationships.

## Statement evidence

- Statement: Claude Code MemSearch installs from Claude Code Marketplace with `/plugin marketplace add zilliztech/memsearch` and `/plugin install memsearch`.
  Evidence: `docs/platforms/claude-code/installation.md:3-16`.
- Statement: Claude Code must restart after install and update.
  Evidence: `docs/platforms/claude-code/installation.md:10-15`; `docs/platforms/claude-code/installation.md:50-60`.
- Statement: OpenClaw MemSearch installs from ClawHub with `openclaw plugins install --force clawhub:memsearch`.
  Evidence: `docs/platforms/openclaw/installation.md:9-23`.
- Statement: OpenClaw requires `allowConversationAccess` to read conversation turns and `allowPromptInjection` to inject recall context.
  Evidence: `docs/platforms/openclaw/installation.md:17-22`; `docs/platforms/openclaw/installation.md:34-39`.
- Statement: OpenClaw defaults `autoCapture` and `autoRecall` to true.
  Evidence: `docs/platforms/openclaw/installation.md:42-54`.
- Statement: OpenClaw updates by reinstalling from ClawHub and restarting the gateway.
  Evidence: `docs/platforms/openclaw/installation.md:56-65`.
- Statement: OpenCode npm install adds `@zilliz/memsearch-opencode` to `~/.config/opencode/opencode.json`.
  Evidence: `docs/platforms/opencode/installation.md:45-53`.
- Statement: OpenCode source installer symlinks plugin and memory-recall skill, installs npm dependencies, and shows next steps.
  Evidence: `docs/platforms/opencode/installation.md:55-66`.
- Statement: OpenCode requires POSIX shell helper scripts with `bash` and `python3`, and native Windows is not supported yet.
  Evidence: `docs/platforms/opencode/installation.md:3-18`.
- Statement: OpenCode Windows recommendations are WSL2 or Git Bash / another POSIX-compatible shell.
  Evidence: `docs/platforms/opencode/installation.md:10-18`.
- Statement: OpenCode native Windows support is tracked by issue #387.
  Evidence: `docs/platforms/opencode/installation.md:18`.
- Statement: OpenCode npm updates keep `@zilliz/memsearch-opencode` in `opencode.json` and restart OpenCode.
  Evidence: `docs/platforms/opencode/installation.md:77-87`.
- Statement: Codex installer copies memory-recall skill, updates hooks in `~/.codex/hooks.json`, enables `hooks = true`, and makes scripts executable.
  Evidence: `docs/platforms/codex/installation.md:9-25`.
- Statement: Codex usage requires full access on first run for ONNX model download and hooks execute shell commands.
  Evidence: `docs/platforms/codex/installation.md:26-39`.
- Statement: Codex update preserves the ONNX extra and reruns the installer.
  Evidence: `docs/platforms/codex/installation.md:120-128`.
- Statement: Claude Code uninstall does not delete `.memsearch/memory`.
  Evidence: `docs/platforms/claude-code/installation.md:71-77`.
- Statement: OpenClaw uninstall does not delete `.memsearch/memory`.
  Evidence: `docs/platforms/openclaw/installation.md:78-85`.
- Statement: OpenCode uninstall does not delete `.memsearch/memory`.
  Evidence: `docs/platforms/opencode/installation.md:97-108`.
- Statement: Codex uninstall removes only MemSearch hook entries and skill, preserves unrelated Codex hooks, and does not delete `.memsearch/memory`.
  Evidence: `docs/platforms/codex/installation.md:64-118`.
- Statement: Platform install route names are Claude Code Marketplace, OpenClaw ClawHub, OpenCode npm, and Codex CLI installer script.
  Evidence: `docs/platforms/claude-code/installation.md:3-16`; `docs/platforms/openclaw/installation.md:9-23`; `docs/platforms/opencode/installation.md:45-59`; `docs/platforms/codex/installation.md:9-25`.
- Statement: Codex installer writes the memory-recall skill to `~/.agents/skills`, hooks to `~/.codex/hooks.json`, and enables `hooks = true`.
  Evidence: `docs/platforms/codex/installation.md:19-25`.
- Statement: Plugin uninstall does not delete `.memsearch/memory` for Claude Code, OpenClaw, OpenCode, or Codex.
  Evidence: `docs/platforms/claude-code/installation.md:71-77`; `docs/platforms/openclaw/installation.md:78-85`; `docs/platforms/opencode/installation.md:97-108`; `docs/platforms/codex/installation.md:64-118`.
- Statement: OpenCode native Windows support is tracked by issue #387.
  Evidence: `docs/platforms/opencode/installation.md:10-18`.
