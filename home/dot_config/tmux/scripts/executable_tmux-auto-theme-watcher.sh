#!/usr/bin/env bash
# tmux-auto-theme-watcher.sh — background daemon that watches for macOS dark/light mode changes.
#
# Runs in the background and checks AppleInterfaceStyle every 30 seconds.
# When a change is detected, reloads the tmux color theme automatically.
#
# Start:  ~/.config/tmux/scripts/tmux-auto-theme-watcher.sh &
# Stop:   kill "$(cat ~/.config/tmux/theme-watcher.pid 2>/dev/null)"
#
# Called from: shell profile (e.g. .zshrc) via a background watcher startup.

set -uo pipefail

COLORS_DIR="$HOME/.config/tmux/colors"
LOCKFILE="$HOME/.config/tmux/theme-lock"
PIDFILE="$HOME/.config/tmux/theme-watcher.pid"
INTERVAL=30  # seconds between checks

# ── helpers ───────────────────────────────────────────────────────────────────

get_current_theme() {
  if [[ -f "$LOCKFILE" ]]; then
    cat "$LOCKFILE"
  else
    echo "none"
  fi
}

get_os_theme() {
  if [[ "$(uname)" == "Darwin" ]] && defaults read -g AppleInterfaceStyle &>/dev/null; then
    echo "dark"
  else
    echo "light"
  fi
}

apply_theme() {
  local mode="$1"
  local target="$COLORS_DIR/solarized-${mode}.conf"
  if [[ -f "$target" ]]; then
    tmux source-file "$target" 2>/dev/null && echo "$mode" > "$LOCKFILE"
  fi
}

# ── main loop ─────────────────────────────────────────────────────────────────

# Write PID file for easy termination
echo $$ > "$PIDFILE"

# Trap signals for clean shutdown
cleanup() {
  rm -f "$PIDFILE"
  exit 0
}
trap cleanup INT TERM HUP

# Ensure lockfile directory exists
mkdir -p "$HOME/.config/tmux"

# Initial apply (if theme differs from current)
CURRENT=$(get_current_theme)
OS_THEME=$(get_os_theme)
if [[ "$CURRENT" != "$OS_THEME" ]]; then
  apply_theme "$OS_THEME"
fi

# Poll loop
while true; do
  sleep "$INTERVAL" &
  wait $!  # Allow trap to fire during sleep

  CURRENT=$(get_current_theme)
  OS_THEME=$(get_os_theme)
  if [[ "$CURRENT" != "$OS_THEME" ]]; then
    apply_theme "$OS_THEME"
  fi
done
