#!/usr/bin/env bash
# Opens the rename prompt prefilled with the current window name.
# Agent status lives in tmux-agent-tabs (not the window name), so no prefix logic needed.
CURRENT=$(tmux display-message -p '#W')
tmux command-prompt -I "$CURRENT" -p "window name:" "run-shell \"~/.config/tmux/scripts/rename-window.sh '%%'\""
