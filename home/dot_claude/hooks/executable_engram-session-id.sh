#!/bin/sh
# Managed by chezmoi — source: home/dot_claude/hooks/executable_engram-session-id.sh
# SessionStart: tell Claude its Engram session ID. Engram fails closed on writes
# without session_id when several sessions are open in the same directory.
command -v engram >/dev/null 2>&1 || exit 0
id=$(jq -r '.session_id // empty')
if [ -n "$id" ]; then
  echo "Engram session_id: $id. Pass session_id=\"$id\" on every engram write (mem_save, mem_update, mem_session_summary, mem_save_prompt)."
fi
