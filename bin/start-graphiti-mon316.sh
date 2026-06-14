#!/usr/bin/env bash
set -euo pipefail

PROFILE="graphiti-mon316"
COLIMA_HOME="/Volumes/SSD/graphiti-mon316/colima-home"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
ENV_FILE="/Users/dominicmonkhouse/.secrets/graphiti.env"
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SOCKET="$COLIMA_HOME/$PROFILE/docker.sock"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$REPO_ROOT/deploy/graphiti/docker-compose.yml"
COMPOSE_MINI="$REPO_ROOT/deploy/graphiti/docker-compose.mini.yml"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/start.log") 2>&1

echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] starting $PROFILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if [[ -S "$SOCKET" ]]; then
  export DOCKER_HOST="unix://$SOCKET"
  unset DOCKER_CONTEXT
fi

if [[ ! -S "$SOCKET" ]]; then
  COLIMA_HOME="$COLIMA_HOME" colima start "$PROFILE" \
    --runtime docker \
    --cpu 2 \
    --memory 4 \
    --disk 20 \
    --mount /Users/dominicmonkhouse:w \
    --mount /Volumes/SSD:w
fi

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

docker version >/dev/null
docker compose \
  -p "$PROFILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_MINI" \
  up -d

docker update \
  --restart unless-stopped \
  "${PROFILE}-falkordb-1" \
  "${PROFILE}-graphiti-mcp-1" >/dev/null

docker compose \
  -p "$PROFILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_MINI" \
  ps

echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] started $PROFILE"
