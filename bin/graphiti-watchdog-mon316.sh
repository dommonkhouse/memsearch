#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
RUNTIME_ROOT="$HOME/.local/state/graphiti-mon316"
LOG_DIR="$HOME/Library/Logs/graphiti-mon316"
STATE_DIR="$HOME/Library/Application Support/graphiti-mon316/state"
COLIMA_PROFILE="graphiti-mon316"
COLIMA_PROFILE_ROOT="$HOME/.colima/$COLIMA_PROFILE"
DOCKER_SOCK="$COLIMA_PROFILE_ROOT/docker.sock"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$STATE_DIR" "$RUNTIME_ROOT"
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
