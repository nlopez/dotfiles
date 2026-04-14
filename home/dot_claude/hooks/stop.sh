#!/usr/bin/env bash
# Sets 👍 when Claude is done, ❓ when the last message appears to be a question.
# Hooked on the Stop event.

[[ -z "$TMUX" ]] && exit 0
source ~/.claude/hooks/lib/tmux-pane.sh

INPUT=$(cat)
PANE=$(find_claude_pane) || exit 0

LAST_MSG=$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // empty')
LAST_CHAR=$(printf '%s' "$LAST_MSG" | tr -d '[:space:]' | tail -c 1)

CURRENT=$(tmux display-message -p -t "$PANE" '#W')
BASE="${CURRENT#🤖 }"; BASE="${BASE#👍 }"; BASE="${BASE#🛎️ }"

if [[ "$LAST_CHAR" == "?" ]]; then
  tmux rename-window -t "$PANE" "🛎️ $BASE"
else
  tmux rename-window -t "$PANE" "👍 $BASE"
fi
