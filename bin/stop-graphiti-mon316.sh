#!/usr/bin/env bash
set -euo pipefail

PROFILE="graphiti-mon316"
COLIMA_HOME="/Volumes/SSD/graphiti-mon316/colima-home"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SOCKET="$COLIMA_HOME/$PROFILE/docker.sock"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$REPO_ROOT/deploy/graphiti/docker-compose.yml"
COMPOSE_MINI="$REPO_ROOT/deploy/graphiti/docker-compose.mini.yml"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/stop.log") 2>&1

echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] stopping $PROFILE"

if [[ ! -S "$SOCKET" ]]; then
  echo "Could not find dedicated Docker socket: $SOCKET" >&2
  exit 1
fi

export COLIMA_HOME
export DOCKER_HOST="unix://$SOCKET"
export PATH
unset DOCKER_CONTEXT

if [[ "$DOCKER_HOST" == *"/.colima/default/docker.sock"* ]]; then
  echo "Refusing to run against default Colima socket: $DOCKER_HOST" >&2
  exit 1
fi

docker compose \
  -p "$PROFILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_MINI" \
  down

if [[ "${1:-}" == "--stop-colima" ]]; then
  COLIMA_HOME="$COLIMA_HOME" colima stop "$PROFILE"
fi

if docker context inspect colima >/dev/null 2>&1; then
  docker context use colima >/dev/null 2>&1 || true
fi

echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] stopped $PROFILE"
