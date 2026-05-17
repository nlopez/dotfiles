#!/usr/bin/env bash
# Renames the current tmux window, preserving any Claude status emoji prefix.
# Called from bind-key m with the user's desired new name as $1.
NEW_NAME="${1:-untitled}"
[ -z "$NEW_NAME" ] && NEW_NAME="untitled"
CURRENT=$(tmux display-message -p '#W')
BASE=$(printf '%s' "$CURRENT" | sed -E 's/^([🤖✳️🛎️ ])+//')
PREFIX="${CURRENT%"$BASE"}"
tmux rename-window "${PREFIX}${NEW_NAME}"
tmux set-option -w automatic-rename off
