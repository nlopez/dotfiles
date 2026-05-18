#!/usr/bin/env bash
# Clears ✳️ (done) emoji from the previous tmux window when the user switches away.
# Hooked on after-select-window. Tracks the previous window via @last_window.
# Does NOT clear 🤖 (processing) or 🛎️ (needs attention).
CURRENT=$(tmux display-message -p '#{window_id}')
LAST=$(tmux show-option -gvq @last_window 2>/dev/null)

if [[ -n "$LAST" && "$LAST" != "$CURRENT" ]]; then
  LAST_NAME=$(tmux display-message -p -t "$LAST" '#W' 2>/dev/null) || true
  if [[ "$LAST_NAME" == ✳️* ]]; then
    BASE=$(printf '%s' "$LAST_NAME" | sed -E 's/^([🤖✳️🛎️ ])+//')
    tmux rename-window -t "$LAST" "$BASE"
  fi
fi

tmux set-option -g @last_window "$CURRENT"
