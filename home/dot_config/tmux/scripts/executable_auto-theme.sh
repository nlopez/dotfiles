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
#
# Uses a cache file to avoid redundant source-file calls — tmux source-file is
# only invoked when the detected mode actually changes.

set -euo pipefail

CACHE_FILE="${TMPDIR:-/tmp}/tmux-auto-theme"
COLORS_DIR="$HOME/.config/tmux/colors"

# ── detect current appearance ────────────────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]] && defaults read -g AppleInterfaceStyle &>/dev/null; then
  mode="dark"
else
  mode="light"
fi

# ── skip if nothing changed ──────────────────────────────────────────────────
cached=$(cat "$CACHE_FILE" 2>/dev/null || true)
if [[ "$mode" == "$cached" ]]; then
  exit 0
fi

# ── apply and cache ──────────────────────────────────────────────────────────
echo "$mode" > "$CACHE_FILE"
tmux source-file "$COLORS_DIR/solarized-${mode}.conf"
