#!/usr/bin/env bash
# auto-theme.sh — apply the solarized tmux theme that matches the OS appearance.
#
# Called from multiple places:
#   1. tmux.conf via `if-shell` at startup / source-file reload (sets initial theme)
#   2. The client-focus-in hook when the user switches back to the terminal
#   3. The status bar watcher (every 30s) when macOS theme changes mid-session
#
# On macOS: reads AppleInterfaceStyle from NSGlobalDomain.
# On other platforms: always selects "light" (graceful fallback).

set -euo pipefail

COLORS_DIR="$HOME/.config/tmux/colors"

# ── detect current appearance ────────────────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]] && defaults read -g AppleInterfaceStyle &>/dev/null; then
  mode="dark"
else
  mode="light"
fi

# ── Track current theme with a lockfile to avoid redundant reloads ───────────
LOCKFILE="$HOME/.config/tmux/theme-lock"

get_current_theme() {
  if [[ -f "$LOCKFILE" ]]; then
    cat "$LOCKFILE"
  else
    echo "none"
  fi
}

set_current_theme() {
  echo "$1" > "$LOCKFILE"
}

CURRENT_THEME=$(get_current_theme)
if [[ "$CURRENT_THEME" == "$mode" ]]; then
  # Already running this theme — no-op
  exit 0
fi

# Only source the new theme if the file exists
target="$COLORS_DIR/solarized-${mode}.conf"
if [[ -f "$target" ]]; then
  tmux source-file "$target"
fi

set_current_theme "$mode"
