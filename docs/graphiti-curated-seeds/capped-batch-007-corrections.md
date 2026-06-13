<!--
MON-316 capped Graphiti relationship seed batch 007 corrective reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-007-sources.md
-->

# Platform install route anchor relationships

Claude Code MemSearch platform install route is Marketplace.
OpenClaw MemSearch platform install route is ClawHub.
OpenCode MemSearch platform install route is npm.
Codex CLI MemSearch platform install route is the Codex installer script.
Marketplace relates to Claude Code MemSearch installation.
ClawHub relates to OpenClaw MemSearch installation.
npm relates to OpenCode MemSearch installation.

# Codex installer anchor relationships

Codex MemSearch installer writes the memory-recall skill.
Codex MemSearch installer writes to `~/.agents/skills`.
Codex MemSearch installer writes hook entries to `~/.codex/hooks.json`.
Codex MemSearch installer enables `hooks = true`.
Codex MemSearch installer updates skills and hooks.

# Plugin uninstall memory preservation anchors

Claude Code MemSearch uninstall does not delete `.memsearch/memory`.
OpenClaw MemSearch uninstall does not delete `.memsearch/memory`.
OpenCode MemSearch uninstall does not delete `.memsearch/memory`.
Codex MemSearch uninstall does not delete `.memsearch/memory`.
All MemSearch plugin uninstall routes preserve `.memsearch/memory`.

# OpenCode Windows issue anchor relationships

OpenCode native Windows support is tracked by issue #387.
Issue #387 relates to OpenCode native Windows support.
OpenCode native Windows requires POSIX shell workaround until issue #387 is resolved.
