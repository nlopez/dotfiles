#!/usr/bin/env bash
# Renames the current tmux window to the user's desired name.
# Called from bind-key m with the user's desired new name as $1.
# Agent status lives in tmux-agent-tabs (not the window name), so no prefix logic needed.
NEW_NAME="${1:-untitled}"
[ -z "$NEW_NAME" ] && NEW_NAME="untitled"
tmux rename-window "$NEW_NAME"
tmux set-option -w automatic-rename off
