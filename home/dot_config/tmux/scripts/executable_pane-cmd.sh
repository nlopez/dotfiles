#!/usr/bin/env bash
# pane-cmd.sh <pane_pid>
# Prints the foreground command running under <pane_pid>, or "---" when the
# pane is sitting at the shell prompt (i.e. no meaningful child process).
pane_pid="${1:-}"
[[ -z "$pane_pid" ]] && echo "---" && exit 0

child_pid=$(pgrep -nP "$pane_pid" 2>/dev/null)
if [[ -z "$child_pid" ]]; then
  # No child — pane is at the shell prompt.
  echo "---"
  exit 0
fi

cmd=$(ps -o args= -p "$child_pid" 2>/dev/null)
if [[ -z "$cmd" ]]; then
  echo "---"
  exit 0
fi

echo "$cmd"
