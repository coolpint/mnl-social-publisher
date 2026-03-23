#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
COMPOSE_FILE="$REPO_ROOT/deploy/docker-compose.yml"
ENV_FILE="$REPO_ROOT/deploy/mnl-social-publisher.env"
DOCKER_BIN=$(command -v docker || true)

if [[ -z "$DOCKER_BIN" && -x /Applications/Docker.app/Contents/Resources/bin/docker ]]; then
  DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
fi

if [[ -z "$DOCKER_BIN" ]]; then
  echo "Docker CLI not found."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

cd "$REPO_ROOT"
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
