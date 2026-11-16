#!/bin/bash
# Wrapper around chezmoi diff that also shows brew declarative diff.
# Usage: chezmoi-diff [chezmoi diff args...]
#
# Installed as ~/.local/bin/chezmoi-diff by chezmoi.

set -eufo pipefail

CHEZMOI_ROOT="${CHEZMOI_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$0")/../.." )}"

# Run brew declarative preview (darwin only)
if [ "$(uname -s)" = "Darwin" ] && [ -x "$CHEZMOI_ROOT/scripts/brew-declarative-preview.sh" ]; then
  "$CHEZMOI_ROOT/scripts/brew-declarative-preview.sh" darwin
  echo ""
fi

# Run chezmoi diff with any passed args
chezmoi diff "$@"
