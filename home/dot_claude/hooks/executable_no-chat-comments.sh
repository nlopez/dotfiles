#!/bin/sh
# PreToolUse hook: refuse edits whose added text has comments narrating the edit/chat.
PATTERN='(//|#|/\*).*\b(changed from|previously (this|it)|used to be|as requested)\b'
added=$(jq -r '.tool_input | (.new_string // .content // ([.edits[]?.new_string] | join("\n")))')
if printf '%s\n' "$added" | grep -qiE "$PATTERN"; then
  echo "Write comments for the code, not the chat" >&2
  exit 2
fi
