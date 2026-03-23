#!/bin/zsh

set -euo pipefail

PLIST_PATH="$HOME/Library/LaunchAgents/com.moneynlaw.social-publisher.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"

echo "Removed launch agent from $PLIST_PATH"
