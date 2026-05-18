#!/usr/bin/env bash
# Displays a reload message with mtime and relative age of tmux.conf.
# Called from tmux.conf: bind R source-file ...\; run-shell ~/.../reload-notify.sh
# Falls back to a plain message if anything in the enriched path fails.

_notify() {
  local f=~/.config/tmux/tmux.conf
  local mt now age r fmt
  mt=$(stat -c "%Y" "$f" 2>/dev/null || stat -f "%m" "$f") || return 1
  now=$(date +%s)
  age=$(( now - mt ))
  if   [ "$age" -lt 60 ];    then r="${age}s"
  elif [ "$age" -lt 3600 ];  then r="$((age / 60))m"
  elif [ "$age" -lt 86400 ]; then r="$((age / 3600))h"
  else                             r="$((age / 86400))d"
  fi
  fmt=$(date -r "$mt" +"%Y-%m-%d %H:%M" 2>/dev/null || date -d "@$mt" +"%Y-%m-%d %H:%M") || return 1
  tmux display-message -d 5000 "Reloaded tmux.conf — $fmt ($r ago)"
}

_notify || tmux display-message -d 5000 "Reloaded tmux.conf"
