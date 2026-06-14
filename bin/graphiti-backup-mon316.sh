#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/dominicmonkhouse/Projects/memsearch"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
BACKUP_ROOT="/Volumes/SSD/graphiti-mon316/backups"
COLIMA_PROFILE="graphiti-mon316"
COLIMA_HOME="${COLIMA_HOME:-/Volumes/SSD/graphiti-mon316/colima-home}"
DOCKER_SOCK="$COLIMA_HOME/$COLIMA_PROFILE/docker.sock"
PATH="/opt/homebrew/bin:/usr/local/bin:/Users/dominicmonkhouse/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$BACKUP_ROOT"
cd "$REPO_ROOT"

exec >>"$LOG_DIR/backup.log" 2>&1
echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] graphiti backup start"

if [ -f /Users/dominicmonkhouse/.secrets/mcp.env ]; then
  set -a
  source /Users/dominicmonkhouse/.secrets/mcp.env
  set +a
fi

if [ -S "$DOCKER_SOCK" ]; then
  export DOCKER_HOST="unix://$DOCKER_SOCK"
else
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] dedicated Docker socket missing: $DOCKER_SOCK"
  exit 1
fi

uv run memsearch graph-backup --execute --backup-root "$BACKUP_ROOT" --retain-days 30 --prune-to-trash
