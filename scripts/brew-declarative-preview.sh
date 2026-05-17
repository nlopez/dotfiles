#!/bin/bash
# Preview what brew bundle --cleanup would install/remove by comparing
# the current installed state (brew bundle dump) vs the generated config.
#
# Outputs like a git/chezmoi diff: "-" for removals (red), "+" for additions (green).
#
# Usage: scripts/brew-declarative-preview.sh [os]
#   os: darwin (default) or linux
set -ufo pipefail

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

CHEZMOI_ROOT="${CHEZMOI_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$0")/.." )}"
OS="${1:-darwin}"

TMPDIR_WORK=$(mktemp -d)
trap 'rm -rf "$TMPDIR_WORK"' EXIT

# --- Generate Brewfile from config ---
if [ "$OS" = "darwin" ]; then
    GENERATED="$TMPDIR_WORK/generated.brewfile"
    (cd "$CHEZMOI_ROOT" && chezmoi execute-template -f home/dot_Brewfile.tmpl) > "$GENERATED" 2>/dev/null
elif [ "$OS" = "linux" ]; then
    echo "Linux Brew config (no standalone Brewfile to compare):"
    cat "$CHEZMOI_ROOT/home/.chezmoidata/linux/packages.yaml"
    exit 0
else
    echo "Unknown OS: $OS (use darwin or linux)"
    exit 1
fi

# --- Dump current installed state ---
CURRENT="$TMPDIR_WORK/current.brewfile"
brew bundle dump --force --file="$CURRENT" 2>/dev/null

# --- Extract lines of a type, sorted ---
extract_lines() {
    local file="$1" type="$2"
    grep -E "^[[:space:]]*${type} " "$file" 2>/dev/null | sort
}

# --- Color a diff line ---
color_diff() {
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            -*) printf "${RED}%s${NC}" "$line" ;;
            +*) printf "${GREEN}%s${NC}" "$line" ;;
            *)  printf "%s" "$line" ;;
        esac
        printf "\n"
    done
}

# --- Show unified diff for one category, including inline counts ---
show_category() {
    local type="$1"
    local prev_f next_f
    prev_f=$(mktemp)
    next_f=$(mktemp)

    extract_lines "$CURRENT" "$type" > "$prev_f"
    extract_lines "$GENERATED" "$type" > "$next_f"

    local prev_count next_count
    prev_count=$(grep -c . "$prev_f" 2>/dev/null || true)
    next_count=$(grep -c . "$next_f" 2>/dev/null || true)
    prev_count=${prev_count:-0}
    next_count=${next_count:-0}

    # Count additions and removals
    local removed_count added_count
    removed_count=$(comm -23 <(cat "$prev_f") <(cat "$next_f") 2>/dev/null | grep -c . || true)
    added_count=$(comm -13 <(cat "$prev_f") <(cat "$next_f") 2>/dev/null | grep -c . || true)
    removed_count=${removed_count:-0}
    added_count=${added_count:-0}

    # Skip if no changes at all
    if [ "$prev_count" -eq 0 ] && [ "$next_count" -eq 0 ]; then
        rm -f "$prev_f" "$next_f"
        return
    fi

    # Only show if there are actual additions or removals
    if [ "$removed_count" -eq 0 ] && [ "$added_count" -eq 0 ]; then
        rm -f "$prev_f" "$next_f"
        return
    fi

    # Header with counts: (total / +added / -removed)
    echo "--- homebrew: $type ($prev_count / +$added_count / -$removed_count)"
    echo "+++ homebrew: $type (from config)"

    diff -u --label "" --label "" \
        "$prev_f" "$next_f" 2>/dev/null | \
        sed '1,2d' | \
        sed '/^@@/d' | \
        color_diff || true

    echo ""
    rm -f "$prev_f" "$next_f"
}

# --- Diffs ---
for TYPE in tap brew cask mas vscode uv; do
    show_category "$TYPE"
done

echo ""
echo "To apply: chezmoi apply && brew bundle --global --cleanup"
