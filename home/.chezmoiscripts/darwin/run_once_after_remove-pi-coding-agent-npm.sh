#!/bin/bash

# Remove the legacy npm-global pi-coding-agent; the managed install at
# ~/.local/bin/pi (installed by run_once_after_install-pi-coding-agent.sh) replaces it.
set -eufo pipefail

if command -v npm >/dev/null 2>&1 && npm ls -g --depth=0 @earendil-works/pi-coding-agent >/dev/null 2>&1; then
    echo "🗑️  Removing npm-global pi-coding-agent..."
    npm uninstall -g @earendil-works/pi-coding-agent
fi

echo "✅ npm pi-coding-agent removed (managed install takes over)"
