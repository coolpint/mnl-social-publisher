#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
ENV_FILE="$REPO_ROOT/deploy/mnl-social-publisher.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

set -a
. "$ENV_FILE"
set +a

VENV_DIR="${MNL_SOCIAL_VENV_DIR:-$REPO_ROOT/.venv-service}"
GUNICORN_BIN="$VENV_DIR/bin/gunicorn"
HOST="${MNL_SOCIAL_BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8420}"
WORKERS="${WEB_CONCURRENCY:-2}"

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
export PYTHONUNBUFFERED=1

if [[ ! -x "$GUNICORN_BIN" ]]; then
  echo "Gunicorn is missing at $GUNICORN_BIN"
  echo "Run ./scripts/mac_python_bootstrap.sh first."
  exit 1
fi

cd "$REPO_ROOT"
exec "$GUNICORN_BIN" \
  --workers "$WORKERS" \
  --bind "$HOST:$PORT" \
  --chdir "$REPO_ROOT" \
  mnl_social_publisher.wsgi:application
