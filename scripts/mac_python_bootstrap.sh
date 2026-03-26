#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
ENV_FILE="$REPO_ROOT/deploy/mnl-social-publisher.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

resolve_python_bin() {
  if [[ -n "${MNL_SOCIAL_PYTHON_BIN:-}" && -x "${MNL_SOCIAL_PYTHON_BIN}" ]]; then
    echo "${MNL_SOCIAL_PYTHON_BIN}"
    return 0
  fi

  local candidate
  for candidate in \
    /usr/local/bin/python3.13 \
    /opt/homebrew/bin/python3.13 \
    /usr/local/bin/python3.12 \
    /opt/homebrew/bin/python3.12 \
    /usr/local/bin/python3.11 \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.10 \
    /opt/homebrew/bin/python3.10 \
    "$(command -v python3 2>/dev/null || true)"
  do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      if [[ $? -eq 0 ]]; then
        echo "$candidate"
        return 0
      fi
    fi
  done

  return 1
}

PYTHON_BIN=$(resolve_python_bin) || {
  echo "Python 3.10 or newer was not found."
  echo "Set MNL_SOCIAL_PYTHON_BIN in deploy/mnl-social-publisher.env or install Python 3.10+ first."
  exit 1
}

VENV_DIR="${MNL_SOCIAL_VENV_DIR:-$REPO_ROOT/.venv-service}"

echo "Using Python: $PYTHON_BIN"
echo "Virtualenv path: $VENV_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -e "$REPO_ROOT"

echo "Python service environment is ready."
