#!/usr/bin/env bash
# Sets 🤖 on the tmux window title while Claude is processing.
# Hooked on UserPromptSubmit and PostToolUse.

[[ -z "$TMUX" ]] && exit 0
source ~/.claude/hooks/lib/tmux-pane.sh

PANE=$(find_claude_pane) || exit 0

CURRENT=$(tmux display-message -p -t "$PANE" '#W')
BASE=$(strip_window_emoji "$CURRENT")

tmux set-option -w -t "$PANE" automatic-rename off
tmux rename-window -t "$PANE" "🤖 $BASE"
