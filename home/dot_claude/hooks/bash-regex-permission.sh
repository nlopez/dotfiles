#!/usr/bin/env bash
set -euo pipefail

CMD=$(cat | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

DENY_PATTERNS=(
    'find.*-exec'
    '^(fd|fdfind)\s+.*--exec(-batch)?\b'
    'git\s+push\s+.*--force'
    'git\s+push\s+.*--force-with-lease'
    'git\s+reset\s+--hard'
    'git\s+clean\s+-[a-zA-Z]*f'
    'git\s+branch\s+.*-D\b'
    'gh\s+pr\s+close\b'
    'rm\s+-rf\s+[/~]'
    'chmod\s+777'
)

for pattern in "${DENY_PATTERNS[@]}"; do
    if echo "$CMD" | grep -qE "$pattern"; then
        # Fall through to normal permission prompt instead of blocking
        exit 0
    fi
done

ALLOW_PATTERNS=(
    '^kubectl\s+(get|describe|logs|top|explain|version|cluster-info|api-resources|api-versions|diff)\b'
    '^git\s+(status|log|diff|show|branch|blame|tag|stash|fetch|pull|push|checkout|switch|rebase|merge|cherry-pick|revert|commit|add|restore|rm|mv|remote|config|rev-parse|ls-files|ls-tree|shortlog|reflog|describe|name-rev|for-each-ref|worktree)\b'
    '^gh\s+pr\s+(create|edit|merge|view|list|checkout|diff|checks|ready|review|comment)\b'
    '^gh\s+(issue|repo|run|workflow|auth|status)\s'
    '^(cat|head|tail|wc|file|stat|ls|tree)\s'
    '^(grep|rg)\s'
    '^find\s+.*-name\s'
    '^(fd|fdfind)\s'
    '.*(--)?(help|version)$'
    '.*--dry-run\b'
    '^go (list|vet|build|fmt|test|run|mod tidy|mod vendor|mod graph|mod why)\b'
    # system info
    '^(pwd|date|uname|hostname|whoami|id|uptime)\b'
    '^(which|whereis|type)\s'
    '^(env|printenv)\b'
    '^(ps|pgrep)\s'
    '^(df|du)\s'
    '^(lsof)\s'
    # text processing
    '^(diff|delta|colordiff)\s'
    '^(sort|uniq|cut|tr|awk|sed)\s'
    '^(jq|yq)\s'
    '^(bat|less|more)\s'
    # package managers (read-only subcommands)
    '^brew\s+(list|info|search|outdated|leaves|deps|desc|uses)\b'
    '^(npm|yarn|pnpm)\s+(list|info|outdated|ls|why|audit)\b'
    '^pip[0-9]?\s+(list|show|freeze|check)\b'
    '^cargo\s+(check|clippy|doc|metadata|pkgid|locate-project|tree|verify-project)\b'
    # chezmoi read-only
    '^chezmoi\s+(diff|status|data|cat|managed|unmanaged|doctor|dump|execute-template)\b'
    # docker read-only
    '^docker\s+(ps|images|inspect|logs|stats|top|info|version|network ls|volume ls|container ls)\b'
    # misc
    '^(curl|wget)\s.*(-I\b|--head\b)'
    '^(openssl|ssh-keygen)\s.*(--help|-h)\b'
    '^(sw_vers|system_profiler|diskutil list|networksetup -listallnetworkservices)\b'
    '^(xcode-select|xcrun)\s'
)

for pattern in "${ALLOW_PATTERNS[@]}"; do
    if echo "$CMD" | grep -qE "$pattern"; then
        echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Matches allow regex"}}'
        exit 0
    fi
done

exit 0
