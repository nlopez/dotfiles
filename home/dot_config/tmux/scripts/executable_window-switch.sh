#!/usr/bin/env bash
# Clears ✳️ (done) emoji from the previous tmux window when the user switches away,
# but only if they dwelled in that window for more than 3 seconds.
# Hooked on after-select-window. Tracks the previous window via @last_window
# and its entry timestamp via @last_window_entry_time.
# Does NOT clear 🤖 (processing) or 🛎️ (needs attention).
CURRENT=$(tmux display-message -p '#{window_id}')
LAST=$(tmux show-option -gvq @last_window 2>/dev/null)
ENTRY_TIME=$(tmux show-option -gvq @last_window_entry_time 2>/dev/null)
NOW=$(date +%s)

if [[ -n "$LAST" && "$LAST" != "$CURRENT" ]]; then
  LAST_STATUS=$(tmux show-option -wvq -t "$LAST" @pi-status 2>/dev/null || true)
  if [[ "$LAST_STATUS" == ✳️* ]]; then
    DWELL=$(( NOW - ${ENTRY_TIME:-$NOW} ))
    if [[ $DWELL -ge 3 ]]; then
      tmux set-option -wu -t "$LAST" @pi-status 2>/dev/null || true
    fi
  fi
fi

tmux set-option -g @last_window "$CURRENT"
tmux set-option -g @last_window_entry_time "$NOW"
