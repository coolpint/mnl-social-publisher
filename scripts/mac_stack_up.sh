#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
COMPOSE_FILE="$REPO_ROOT/deploy/docker-compose.yml"
ENV_FILE="$REPO_ROOT/deploy/mnl-social-publisher.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Copy deploy/mnl-social-publisher.env.example to deploy/mnl-social-publisher.env and fill in the secrets."
  exit 1
fi

echo "Waiting for Docker daemon..."
for _ in {1..60}; do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not ready. Start Docker Desktop or OrbStack first."
  exit 1
fi

cd "$REPO_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo
echo "Social Desk is starting on http://127.0.0.1:$(grep '^PORT=' "$ENV_FILE" | cut -d= -f2)"
