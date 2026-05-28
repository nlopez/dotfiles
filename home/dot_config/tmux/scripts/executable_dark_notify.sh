#!/usr/bin/env bash
# dark_notify.sh — called by the LaunchAgent to monitor macOS dark/light mode.
# dark-notify -o prints to stdout; pipe to the while loop to process changes.

set -euo pipefail

SCRIPT="$HOME/.config/tmux/scripts/set-theme.sh"

# pipe dark-notify output to the processing loop.
/opt/homebrew/bin/dark-notify -o | while IFS= read -r appearance; do
  [ -z "$appearance" ] && continue
  "$SCRIPT" "$appearance" 2>/dev/null || true
done
