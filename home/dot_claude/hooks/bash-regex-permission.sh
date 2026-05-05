#!/usr/bin/env bash
set -euo pipefail

CMD=$(cat | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Use case statement for O(1) pattern matching
deny_pattern() {
  case "$CMD" in
    *find*--exec*|*fdfind*--exec*|*fdfind*--exec-batch*) return 0 ;;
    git*\ --force*|git*\ --force-with-lease*) return 0 ;;
    git*\ reset\ --hard*) return 0 ;;
    git*\ clean\ -*f*|git*\ clean\ --force*) return 0 ;;
    git*\ branch*\ -D*) return 0 ;;
    gh*\ pr\ close*) return 0 ;;
    rm\ -rf\ /|rm\ -rf\ ~*) return 0 ;;
    chmod\ 777*) return 0 ;;
  esac
  return 1
}

allow_pattern() {
  case "$CMD" in
    # kubectl read-only
    kubectl\ get*|kubectl\ describe*|kubectl\ logs*|kubectl\ top*|kubectl\ explain*|kubectl\ version*|kubectl\ cluster-info*|kubectl\ api-resources*|kubectl\ api-versions*|kubectl\ diff*) return 0 ;;
    # git read-only
    git\ status*|git\ log*|git\ diff*|git\ show*|git\ branch*|git\ blame*|git\ tag*|git\ stash*|git\ fetch*|git\ pull*|git\ checkout*|git\ switch*|git\ rebase*|git\ merge*|git\ cherry-pick*|git\ revert*|git\ add*|git\ restore*|git\ rm*|git\ mv*|git\ remote*|git\ config*|git\ rev-parse*|git\ ls-files*|git\ ls-tree*|git\ shortlog*|git\ reflog*|git\ describe*|git\ name-rev*|git\ for-each-ref*|git\ worktree*) return 0 ;;
    # gh read-only
    gh\ pr\ create*|gh\ pr\ edit*|gh\ pr\ merge*|gh\ pr\ view*|gh\ pr\ list*|gh\ pr\ checkout*|gh\ pr\ diff*|gh\ pr\ checks*|gh\ pr\ ready*|gh\ pr\ review*|gh\ pr\ comment*|gh\ issue*|gh\ repo*|gh\ run*|gh\ workflow*|gh\ auth*|gh\ status*) return 0 ;;
    # file inspection
    cat*|head*|tail*|wc*|file*|stat*|ls*|tree*) return 0 ;;
    # text search
    grep*|rg*) return 0 ;;
    # find with name filter
    find\ *--name*) return 0 ;;
    # fd search
    fd\ *|fdfind\ *) return 0 ;;
    # help/version
    *--help*|*--version*|*\ -h*) return 0 ;;
    *--dry-run*) return 0 ;;
    # go read-only
    go\ list*|go\ vet*|go\ build*|go\ fmt*|go\ test*|go\ run*|go\ mod\ tidy*|go\ mod\ vendor*|go\ mod\ graph*|go\ mod\ why*) return 0 ;;
    # system info
    pwd*|date*|uname*|hostname*|whoami*|id*|uptime*) return 0 ;;
    which*|whereis*|type*) return 0 ;;
    env*|printenv*) return 0 ;;
    ps*\ *|pgrep*) return 0 ;;
    df*\ *|du*\ *) return 0 ;;
    lsof*) return 0 ;;
    # text processing
    diff*\ *|delta*\ *|colordiff*\ *) return 0 ;;
    sort*\ *|uniq*\ *|cut*\ *|tr*\ *|awk*\ *|sed*\ *) return 0 ;;
    jq*\ *|yq*\ *) return 0 ;;
    bat*\ *|less*\ *|more*\ *) return 0 ;;
    # package managers (read-only)
    brew\ list*|brew\ info*|brew\ search*|brew\ outdated*|brew\ leaves*|brew\ deps*|brew\ desc*|brew\ uses*) return 0 ;;
    npm\ list*|npm\ info*|npm\ outdated*|npm\ ls*|npm\ why*|npm\ audit*) return 0 ;;
    yarn\ list*|yarn\ info*|yarn\ outdated*|yarn\ ls*|yarn\ why*|yarn\ audit*) return 0 ;;
    pnpm\ list*|pnpm\ info*|pnpm\ outdated*) return 0 ;;
    pip*\ list*|pip*\ show*|pip*\ freeze*|pip*\ check*|pip0*\ list*|pip0*\ show*|pip0*\ freeze*|pip0*\ check*) return 0 ;;
    pipenv\ graph*|pipenv\ run*\ --help*) return 0 ;;
    poetry\ show*|poetry\ info*|poetry\ tree*|poetry\ check*|poetry\ run*\ --help*) return 0 ;;
    cargo\ check*|cargo\ clippy*|cargo\ doc*|cargo\ metadata*|cargo\ pkgid*|cargo\ locate-project*|cargo\ tree*|cargo\ verify-project*) return 0 ;;
    # chezmoi read-only
    chezmoi\ diff*|chezmoi\ status*|chezmoi\ data*|chezmoi\ cat*|chezmoi\ managed*|chezmoi\ unmanaged*|chezmoi\ doctor*|chezmoi\ dump*|chezmoi\ execute-template*) return 0 ;;
    # docker read-only
    docker\ ps*|docker\ images*|docker\ inspect*|docker\ logs*|docker\ stats*|docker\ top*|docker\ info*|docker\ version*|docker\ network\ ls*|docker\ volume\ ls*|docker\ container\ ls*) return 0 ;;
    # misc
    curl\ -I*|curl\ --head*|wget\ --server-response*|wget\ --spider*) return 0 ;;
    openssl*\ --help*|ssh-keygen*\ --help*) return 0 ;;
    sw_vers*|system_profiler*\ *|diskutil\ list*|networksetup\ -listallnetworkservices*) return 0 ;;
    xcode-select*\ *|xcrun*\ *) return 0 ;;
  esac
  return 1
}

if deny_pattern; then
  exit 0
fi

if allow_pattern; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Matches allow regex"}}'
  exit 0
fi

exit 0
