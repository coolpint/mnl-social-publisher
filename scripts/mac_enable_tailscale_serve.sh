#!/bin/zsh

set -euo pipefail

TAILSCALE_BIN=$(command -v tailscale || true)

if [[ -z "$TAILSCALE_BIN" && -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ]]; then
  TAILSCALE_BIN=/Applications/Tailscale.app/Contents/MacOS/Tailscale
fi

if [[ -z "$TAILSCALE_BIN" ]]; then
  echo "Tailscale CLI not found."
  exit 1
fi

"$TAILSCALE_BIN" serve --bg 8420
"$TAILSCALE_BIN" serve status
