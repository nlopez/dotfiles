#!/usr/bin/env bash
# Pre-commit hook: reject files whose plaintext matches a private pattern.
# Patterns (extended regexes, case-insensitive, one per line) are rendered from
# the private data to ~/.config/dotfiles/private-patterns.txt; see
# docs/private-data.md. Encrypted *.age files are skipped.
set -euo pipefail

patterns="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/private-patterns.txt"
if [[ ! -s "$patterns" ]]; then
  echo "private-patterns: $patterns not found; skipping (run chezmoi apply on a work machine)" >&2
  exit 0
fi

files=()
for f in "$@"; do
  [[ "$f" == *.age || ! -f "$f" ]] || files+=("$f")
done
[[ ${#files[@]} -gt 0 ]] || exit 0

if grep -I -n -i -E -f <(grep -v '^[[:space:]]*$' "$patterns") -- "${files[@]}"; then
  echo "private-patterns: move these values into the private data (docs/private-data.md)" >&2
  exit 1
fi
