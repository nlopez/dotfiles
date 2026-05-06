#!/usr/bin/env bash
# Finds the tmux pane ID for the current Claude session by walking up
# the process tree from the hook process to the shell running in a tmux pane.
#
# Usage: source this file, then call find_claude_pane
# Returns: pane ID (e.g. %3) via stdout, exit 1 if not found

strip_window_emoji() {
  local name="$1"
  echo "$name" | sed -E 's/^([🤖✳️🛎️ ])+//'
}

find_claude_pane() {
  local pane_id pane_pid current

  declare -A pane_map
  while IFS=' ' read -r pane_id pane_pid; do
    pane_map[$pane_pid]=$pane_id
  done < <(tmux list-panes -a -F '#{pane_id} #{pane_pid}')

  declare -A parent_map
  while IFS=' ' read -r pid ppid; do
    parent_map[$pid]=$ppid
  done < <(ps -Ao pid=,ppid= 2>/dev/null)

  current=$PPID
  while [[ -n "$current" && "$current" -gt 1 ]]; do
    if [[ -n "${pane_map[$current]}" ]]; then
      echo "${pane_map[$current]}"
      return 0
    fi
    current=${parent_map[$current]}
  done

  return 1
}
