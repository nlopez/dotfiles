#!/bin/bash

# Remove Homebrew pi-coding-agent; replaced by pnpm global install so `pi update` works.
set -eufo pipefail

if brew list --formula 2>/dev/null | grep -q '^pi-coding-agent$'; then
    echo "🗑️  Removing Homebrew pi-coding-agent..."
    brew uninstall pi-coding-agent
fi

echo "✅ Homebrew pi-coding-agent removed (pnpm global install takes over)"
