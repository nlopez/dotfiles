#!/usr/bin/env bash
# Clears ✳️ (done) emoji from the previous tmux window when the user switches away,
# but only if they dwelled in that window for more than 10 seconds.
# Hooked on after-select-window. Tracks the previous window via @last_window
# and its entry timestamp via @last_window_entry_time.
# Does NOT clear 🤖 (processing) or 🛎️ (needs attention).
CURRENT=$(tmux display-message -p '#{window_id}')
LAST=$(tmux show-option -gvq @last_window 2>/dev/null)
ENTRY_TIME=$(tmux show-option -gvq @last_window_entry_time 2>/dev/null)
NOW=$(date +%s)

if [[ -n "$LAST" && "$LAST" != "$CURRENT" ]]; then
  LAST_NAME=$(tmux display-message -p -t "$LAST" '#W' 2>/dev/null) || true
  if [[ "$LAST_NAME" == ✳️* ]]; then
    DWELL=$(( NOW - ${ENTRY_TIME:-$NOW} ))
    if [[ $DWELL -ge 10 ]]; then
      BASE=$(printf '%s' "$LAST_NAME" | sed -E 's/^([🤖✳️🛎️ ])+//')
      tmux rename-window -t "$LAST" "$BASE"
    fi
  fi
fi

tmux set-option -g @last_window "$CURRENT"
tmux set-option -g @last_window_entry_time "$NOW"
