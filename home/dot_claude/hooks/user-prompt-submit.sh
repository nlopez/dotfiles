#!/usr/bin/env bash
# Sets 🤖 on the tmux window title while Claude is processing.
# Hooked on the UserPromptSubmit event.

[[ -z "$TMUX" ]] && exit 0
source ~/.claude/hooks/lib/tmux-pane.sh

PANE=$(find_claude_pane) || exit 0

CURRENT=$(tmux display-message -p -t "$PANE" '#W')
BASE="${CURRENT#🤖 }"; BASE="${BASE#👍 }"; BASE="${BASE#❓ }"

tmux set-option -w -t "$PANE" automatic-rename off
tmux rename-window -t "$PANE" "🤖 $BASE"
