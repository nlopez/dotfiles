#!/usr/bin/env bash
# set-theme.sh [dark|light]
#
# Applies the correct tmux status-bar palette for Atom One Dark or Solarized Light.
# Argument takes priority; falls back to APP_APPEARANCE (set by dark-notify --exec),
# then to detecting the current macOS system appearance.

set -euo pipefail

APPEARANCE="${1:-${APP_APPEARANCE:-}}"
if [ -z "$APPEARANCE" ]; then
  raw=$(defaults read -g AppleInterfaceStyle 2>/dev/null || echo "Light")
  APPEARANCE=$(echo "$raw" | tr '[:upper:]' '[:lower:]')
  [ "$APPEARANCE" = "dark" ] || APPEARANCE="light"
fi

if [ "$APPEARANCE" = "dark" ]; then
  # ── Atom One Dark ──────────────────────────────────────────────────────────
  STATUS="bg=#21252b,fg=#abb2bf"
  WIN="bg=#21252b,fg=#5c6370"
  WIN_CUR="bg=#61afef,fg=#21252b,bold"
  WIN_BELL="bg=#e06c75,fg=#ffffff"
  PANE="fg=#3e4452"
  PANE_ACT="fg=#61afef"
  MSG="bg=#61afef,fg=#21252b"
else
  # ── Solarized Light ────────────────────────────────────────────────────────
  STATUS="bg=#fdf6e3,fg=#657b83"
  WIN="bg=#fdf6e3,fg=#93a1a1"
  WIN_CUR="bg=#268bd2,fg=#fdf6e3,bold"
  WIN_BELL="bg=#dc322f,fg=#fdf6e3"
  PANE="fg=#eee8d5"
  PANE_ACT="fg=#268bd2"
  MSG="bg=#268bd2,fg=#fdf6e3"
fi

tmux set-option -g status-style                "$STATUS"   2>/dev/null || true
tmux set-option -g window-status-style         "$WIN"      2>/dev/null || true
tmux set-option -g window-status-current-style "$WIN_CUR"  2>/dev/null || true
tmux set-option -g window-status-bell-style    "$WIN_BELL" 2>/dev/null || true
tmux set-option -g pane-border-style           "$PANE"     2>/dev/null || true
tmux set-option -g pane-active-border-style    "$PANE_ACT" 2>/dev/null || true
tmux set-option -g message-style               "$MSG"      2>/dev/null || true

# Force tmux to redraw the status bar immediately (status-interval=5 alone is too slow)
tmux refresh-pane -t - 2>/dev/null || true
