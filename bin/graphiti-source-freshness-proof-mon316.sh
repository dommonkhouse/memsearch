#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
FALLBACK_LOG_DIR="$HOME/Library/Logs/graphiti-mon316"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if ! (mkdir -p "$LOG_DIR" && : >"$LOG_DIR/.write-test" && rm -f "$LOG_DIR/.write-test") 2>/dev/null; then
  LOG_DIR="$FALLBACK_LOG_DIR"
fi

mkdir -p "$LOG_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/source-freshness-proof.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] source freshness proof start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] warning: /Users/dominicmonkhouse/.secrets/mcp.env not found"
fi

uv run python -m memsearch.backfill.cli source-freshness --run-proof
