#!/usr/bin/env bash
# Sets ❓ when Claude explicitly asks a follow-up question mid-task.
# Hooked on PostToolUse with matcher AskFollowupQuestion.

[[ -z "$TMUX" ]] && exit 0
source ~/.claude/hooks/lib/tmux-pane.sh

PANE=$(find_claude_pane) || exit 0

CURRENT=$(tmux display-message -p -t "$PANE" '#W')
BASE="${CURRENT#🤖 }"; BASE="${BASE#👍 }"; BASE="${BASE#🛎️ }"

tmux rename-window -t "$PANE" "🛎️ $BASE"
bash ~/.claude/hooks/notification.sh "Waiting for input" <<< '{}'
