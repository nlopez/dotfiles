#!/usr/bin/env bash
# auto-theme.sh — apply the solarized tmux theme that matches the OS appearance.
#
# Called from two places:
#   1. tmux.conf via `if-shell` at startup / source-file reload (sets initial theme)
#   2. The client-focus-in hook so the theme updates when the user switches back
#      to the terminal after changing the system appearance.
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

tmux source-file "$COLORS_DIR/solarized-${mode}.conf"
