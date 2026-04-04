#!/usr/bin/env bash
set -euo pipefail

CMD=$(cat | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

DENY_PATTERNS=(
    'find.*-exec'
    '^(fd|fdfind)\s+.*--exec(-batch)?\b'
    'git\s+push\s+--force'
    'git\s+reset\s+--hard'
    'rm\s+-rf\s+[/~]'
    'chmod\s+777'
)

for pattern in "${DENY_PATTERNS[@]}"; do
    if echo "$CMD" | grep -qE "$pattern"; then
        echo "BLOCKED: Command matches deny pattern: $pattern" >&2
        exit 2
    fi
done

ALLOW_PATTERNS=(
    '^kubectl\s+(get|describe|logs|top|explain|version|cluster-info|api-resources|api-versions|diff)\b'
    '^git\s+(status|log|diff|show|branch|blame|tag)\b'
    '^(cat|head|tail|wc|file|stat|ls|tree)\s'
    '^(grep|rg)\s'
    '^find\s+.*-name\s'
    '^(fd|fdfind)\s'
    '.*--help$'
    '.*--version$'
    '.*--dry-run\b'
)

for pattern in "${ALLOW_PATTERNS[@]}"; do
    if echo "$CMD" | grep -qE "$pattern"; then
        echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Matches allow regex"}}'
        exit 0
    fi
done

exit 0
