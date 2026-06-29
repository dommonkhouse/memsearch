#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="$HOME/Library/Logs/graphiti-mon316"
TODAY="$(date '+%Y-%m-%d')"
OUTPUT_DIR="$REPO_ROOT/outputs/$TODAY"
CURATED_SEEDS_DIR="${CURATED_SEEDS_DIR:-$REPO_ROOT/docs/graphiti-curated-seeds}"
CLAUDE_MEMORY_DIR="${CLAUDE_MEMORY_DIR:-/Users/dominicmonkhouse/Projects/claude-config/memory}"
LINEAR_MEMORY_DIR="${LINEAR_MEMORY_DIR:-/Users/dominicmonkhouse/Projects/.memsearch/memory/linear}"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/candidate-report.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti candidate report start"

uv run memsearch graph-candidate-report \
  "$CURATED_SEEDS_DIR" \
  "$CLAUDE_MEMORY_DIR" \
  "$LINEAR_MEMORY_DIR" \
  --output "$OUTPUT_DIR/graphiti-candidate-report.md"
