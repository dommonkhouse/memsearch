#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

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
