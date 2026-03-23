#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
PLIST_TEMPLATE="$REPO_ROOT/deploy/com.moneynlaw.social-publisher.plist.template"
LOG_DIR="$REPO_ROOT/deploy/logs"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/com.moneynlaw.social-publisher.plist"

mkdir -p "$LOG_DIR"
mkdir -p "$LAUNCH_AGENTS_DIR"

python3 - "$PLIST_TEMPLATE" "$PLIST_PATH" "$REPO_ROOT" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
repo_root = sys.argv[3]

content = template_path.read_text(encoding="utf-8").replace("__REPO_ROOT__", repo_root)
output_path.write_text(content, encoding="utf-8")
PY

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/com.moneynlaw.social-publisher"

echo "Installed launch agent at $PLIST_PATH"
