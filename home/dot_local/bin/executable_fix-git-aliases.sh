#!/usr/bin/env bash
# fix-git-aliases.sh — find and convert git remotes that still use SSH host
# aliases to natural github.com URLs.
#
# Since identity selection now happens via core.sshCommand in per-repo git
# config includes, remotes should use plain git@github.com:org/repo.git URLs.
# Any remote using an old SSH alias (github.com-work, github.com-personal,
# github.com-nlopez, github.com-nick-lopez_ddog, github.com-silentshout42,
# github.com-ddog, github.com-hobby) needs to be rewritten.
#
# Usage:
#   fix-git-aliases.sh            # dry-run: list affected repos and changes
#   fix-git-aliases.sh --fix      # apply rewrites in-place

set -euo pipefail

SEARCH_DIR="${HOME}/src/github.com"

# All known SSH alias patterns (old and new).
ALIAS_RE='git@github\.com-(nlopez|nick-lopez_ddog|silentshout42|work|personal|ddog|hobby):'

alias_to_natural() {
  local url="$1"
  # git@github.com-ALIAS:org/repo  →  git@github.com:org/repo
  echo "$url" | sed -E 's|git@github\.com-[^:]+:|git@github.com:|'
}

echo "============================================================"
echo "  Git Remote Alias Fixer"
echo "============================================================"
echo ""
echo "Converts: git@github.com-<alias>:org/repo"
echo "      to: git@github.com:org/repo"
echo ""
echo "core.sshCommand in the per-repo git config include selects"
echo "the right identity — no host alias needed in the URL."
echo ""

if [[ ! -d "$SEARCH_DIR" ]]; then
  echo "Search directory $SEARCH_DIR not found. Nothing to do."
  exit 0
fi

declare -a repos=()
declare -a old_urls=()
declare -a new_urls=()
declare -a remote_names=()

while IFS= read -r -d '' git_dir; do
  repo_dir="$(dirname "$git_dir")"

  while IFS= read -r remote; do
    url=$(git -C "$repo_dir" remote get-url "$remote" 2>/dev/null || true)
    if [[ "$url" =~ $ALIAS_RE ]]; then
      fixed=$(alias_to_natural "$url")
      repos+=("${repo_dir#$HOME/}")
      remote_names+=("$remote")
      old_urls+=("$url")
      new_urls+=("$fixed")
    fi
  done < <(git -C "$repo_dir" remote 2>/dev/null | tr '\n' '\0')

done < <(find "$SEARCH_DIR" -name .git -type d -print0 2>/dev/null)

if [[ ${#repos[@]} -eq 0 ]]; then
  echo "No remotes with SSH aliases found under $SEARCH_DIR."
  exit 0
fi

echo "Found ${#repos[@]} remote(s) to fix:"
echo ""
for i in "${!repos[@]}"; do
  echo "  ${repos[$i]}"
  echo "    remote : ${remote_names[$i]}"
  echo "    before : ${old_urls[$i]}"
  echo "    after  : ${new_urls[$i]}"
  echo ""
done

if [[ "${1:-}" == "--fix" ]]; then
  echo "Applying..."
  for i in "${!repos[@]}"; do
    repo_dir="$HOME/${repos[$i]}"
    git -C "$repo_dir" remote set-url "${remote_names[$i]}" "${new_urls[$i]}"
    echo "  fixed: ${repos[$i]} (${remote_names[$i]})"
  done
  echo ""
  echo "Done. Verify with: git remote -v"
else
  echo "Dry run — no changes made. Re-run with --fix to apply."
fi
