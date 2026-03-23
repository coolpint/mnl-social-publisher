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
  echo "Docker CLI not found. Start Docker Desktop or install OrbStack first."
  exit 1
fi

case ":$PATH:" in
  *:/Applications/Docker.app/Contents/Resources/bin:*) ;;
  *) export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ;;
esac

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Copy deploy/mnl-social-publisher.env.example to deploy/mnl-social-publisher.env and fill in the secrets."
  exit 1
fi

echo "Waiting for Docker daemon..."
for _ in {1..60}; do
  if "$DOCKER_BIN" info >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! "$DOCKER_BIN" info >/dev/null 2>&1; then
  echo "Docker daemon is not ready. Start Docker Desktop or OrbStack first."
  exit 1
fi

cd "$REPO_ROOT"
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo
echo "Social Desk is starting on http://127.0.0.1:$(grep '^PORT=' "$ENV_FILE" | cut -d= -f2)"
