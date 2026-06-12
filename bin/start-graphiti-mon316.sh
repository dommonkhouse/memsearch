#!/usr/bin/env bash
set -euo pipefail

PROFILE="graphiti-mon316"
COLIMA_HOME="/Volumes/SSD/graphiti-mon316/colima-home"
LOG_DIR="/Volumes/SSD/graphiti-mon316/logs"
ENV_FILE="/Users/dominicmonkhouse/.secrets/graphiti.env"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$REPO_ROOT/deploy/graphiti/docker-compose.yml"
COMPOSE_MINI="$REPO_ROOT/deploy/graphiti/docker-compose.mini.yml"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/start.log") 2>&1

echo "[$(date -Is)] starting $PROFILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if ! COLIMA_HOME="$COLIMA_HOME" colima status "$PROFILE" >/dev/null 2>&1; then
  COLIMA_HOME="$COLIMA_HOME" colima start "$PROFILE" \
    --runtime docker \
    --cpu 2 \
    --memory 4 \
    --disk 20 \
    --mount /Users/dominicmonkhouse:w \
    --mount /Volumes/SSD:w
fi

SOCKET="$(/usr/bin/find "$COLIMA_HOME" -name docker.sock -type s -print | /usr/bin/grep "/$PROFILE/docker.sock" | /usr/bin/head -n 1)"
if [[ -z "$SOCKET" ]]; then
  echo "Could not find dedicated Docker socket under $COLIMA_HOME" >&2
  exit 1
fi

export COLIMA_HOME
export DOCKER_HOST="unix://$SOCKET"
unset DOCKER_CONTEXT

if [[ "$DOCKER_HOST" == *"/.colima/default/docker.sock"* ]]; then
  echo "Refusing to run against default Colima socket: $DOCKER_HOST" >&2
  exit 1
fi

if ! docker context inspect colima >/dev/null 2>&1; then
  echo "Default Colima Docker context missing; continuing with DOCKER_HOST=$DOCKER_HOST"
else
  docker context use colima >/dev/null 2>&1 || true
fi

docker version >/dev/null
docker compose \
  -p "$PROFILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_MINI" \
  up -d

docker compose \
  -p "$PROFILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_MINI" \
  ps

echo "[$(date -Is)] started $PROFILE"
