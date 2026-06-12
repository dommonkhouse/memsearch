#!/usr/bin/env bash
set -euo pipefail

export HOME="/Users/dominicmonkhouse"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec /usr/bin/ssh \
  -F /dev/null \
  -N \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o IdentityFile=/Users/dominicmonkhouse/.ssh/id_ed25519 \
  -o UserKnownHostsFile=/Users/dominicmonkhouse/.ssh/known_hosts \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L 100.72.169.59:8018:127.0.0.1:18018 \
  localhost
