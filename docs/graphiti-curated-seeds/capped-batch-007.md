<!--
MON-316 capped Graphiti relationship seed batch 007.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-007-sources.md
-->

# Platform install route relationships

Claude Code MemSearch install route is the Claude Code Marketplace.
Claude Code Marketplace install uses `/plugin marketplace add zilliztech/memsearch`.
Claude Code Marketplace install uses `/plugin install memsearch`.
Claude Code must restart after installing MemSearch from Marketplace.
OpenClaw MemSearch install route is ClawHub.
OpenClaw ClawHub install uses `openclaw plugins install --force clawhub:memsearch`.
OpenClaw must restart the gateway after installing MemSearch.
OpenCode MemSearch install route is npm.
OpenCode npm install adds `@zilliz/memsearch-opencode` to `~/.config/opencode/opencode.json`.
OpenCode source install runs `bash memsearch/plugins/opencode/install.sh`.
Codex CLI MemSearch install route is the repo installer script.
Codex CLI installer runs `bash memsearch/plugins/codex/scripts/install.sh`.

# OpenClaw permission relationships

OpenClaw MemSearch requires `allowConversationAccess`.
`allowConversationAccess` lets MemSearch read conversation turns.
OpenClaw MemSearch requires `allowPromptInjection`.
`allowPromptInjection` lets MemSearch inject recall context.
OpenClaw MemSearch defaults `autoCapture` to true.
OpenClaw MemSearch defaults `autoRecall` to true.

# Codex installer relationships

Codex MemSearch installer copies the memory-recall skill to `~/.agents/skills/`.
Codex MemSearch installer installs or updates MemSearch hooks in `~/.codex/hooks.json`.
Codex MemSearch installer enables `hooks = true` in `~/.codex/config.toml`.
Codex MemSearch installer makes all scripts executable.
Codex MemSearch usage requires full access on first run for ONNX model download.
Codex MemSearch hooks execute shell commands.

# Plugin update and uninstall relationships

Claude Code MemSearch update uses Claude plugin marketplace update commands.
Claude Code must restart after updating MemSearch so new hooks and skill files load.
OpenClaw MemSearch update reinstalls from ClawHub and restarts the gateway.
OpenCode MemSearch npm update keeps `@zilliz/memsearch-opencode` in `opencode.json` and restarts OpenCode.
Codex MemSearch update preserves the ONNX extra with `uv tool install -U "memsearch[onnx]"`.
Codex MemSearch update reruns the Codex installer.
Claude Code uninstall does not delete `.memsearch/memory`.
OpenClaw uninstall does not delete `.memsearch/memory`.
OpenCode uninstall does not delete `.memsearch/memory`.
Codex uninstall does not delete `.memsearch/memory`.
Codex uninstall preserves unrelated Codex hooks.

# OpenCode Windows and POSIX shell relationships

OpenCode MemSearch requires a POSIX shell environment for helper scripts.
OpenCode MemSearch helper scripts use `bash` and `python3`.
OpenCode native Windows is not supported yet.
OpenCode native Windows without a POSIX shell can fail with `derive-collection.sh: No such file or directory`.
OpenCode Windows recommendation is WSL2 for OpenCode plus MemSearch.
OpenCode Windows alternative is Git Bash or another POSIX-compatible shell.
OpenCode native Windows support is tracked by issue #387.
