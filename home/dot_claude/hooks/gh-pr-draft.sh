#!/usr/bin/env bash
input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // ""')

if echo "$cmd" | grep -qE 'gh pr create' && ! echo "$cmd" | grep -q -- '--draft'; then
    new_cmd=$(echo "$cmd" | sed 's/gh pr create/gh pr create --draft/')
    jq -n --arg cmd "$new_cmd" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", updatedInput: {command: $cmd}}}'
fi
