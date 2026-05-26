#!/usr/bin/env bash
# Opens the rename prompt prefilled with the current window name.
# Emoji status lives in @pi-status (not the window name), so no stripping needed.
CURRENT=$(tmux display-message -p '#W')
tmux command-prompt -I "$CURRENT" -p "window name:" "run-shell \"~/.config/tmux/scripts/rename-window.sh '%%'\""
