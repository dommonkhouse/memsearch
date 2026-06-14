#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
FALLBACK_LOG_DIR="$HOME/Library/Logs/graphiti-mon316"
STATE_DIR="/Volumes/SSD/graphiti-mon316/state"
FALLBACK_STATE_DIR="$HOME/Library/Application Support/graphiti-mon316/state"
COLIMA_PROFILE="graphiti-mon316"
COLIMA_HOME="${COLIMA_HOME:-/Volumes/SSD/graphiti-mon316/colima-home}"
DOCKER_SOCK="$COLIMA_HOME/$COLIMA_PROFILE/docker.sock"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if ! mkdir -p "$LOG_DIR" "$STATE_DIR" 2>/dev/null || [ ! -w "$LOG_DIR" ] || [ ! -w "$STATE_DIR" ]; then
  LOG_DIR="$FALLBACK_LOG_DIR"
  STATE_DIR="$FALLBACK_STATE_DIR"
fi

mkdir -p "$LOG_DIR" "$STATE_DIR"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/watchdog.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti watchdog start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
fi

if [ -S "$DOCKER_SOCK" ]; then
  export DOCKER_HOST="unix://$DOCKER_SOCK"
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] dedicated Docker socket missing: $DOCKER_SOCK"
fi

uv run memsearch graph-watchdog \
  --execute \
  --state-path "$STATE_DIR/watchdog.json" \
  --json-output
