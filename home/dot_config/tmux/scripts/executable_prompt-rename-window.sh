#!/usr/bin/env bash
# Opens the rename prompt with the emoji-stripped window name prefilled.
# The rename-window.sh script re-attaches any emoji prefix on confirm.
CURRENT=$(tmux display-message -p '#W')
BASE=$(printf '%s' "$CURRENT" | sed -E 's/^([🤖✳️🛎️ ])+//')
tmux command-prompt -I "$BASE" -p "window name:" "run-shell \"~/.config/tmux/scripts/rename-window.sh '%%'\""
