#!/bin/bash

# Remove the Little Snitch cask; LuLu (casks.base in packages.yaml) replaces it.
set -eufo pipefail

if brew list --cask 2>/dev/null | grep -q '^little-snitch$'; then
    echo "🗑️  Removing Little Snitch (replaced by LuLu)..."
    brew uninstall --cask --zap little-snitch
fi
