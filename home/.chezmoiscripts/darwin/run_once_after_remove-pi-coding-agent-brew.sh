#!/bin/bash

# Remove Homebrew pi-coding-agent; replaced by the managed install so `pi update` works.
set -eufo pipefail

if brew list --formula 2>/dev/null | grep -q '^pi-coding-agent$'; then
    echo "🗑️  Removing Homebrew pi-coding-agent..."
    brew uninstall pi-coding-agent
fi

echo "✅ Homebrew pi-coding-agent removed (managed install takes over)"
