#!/bin/bash
# Remove npm packages that were previously installed as pnpm globals
# but have been moved to pi-managed packages (modify_settings.json).
#
# These packages now live in ~/.pi/agent/npm/ and should be installed
# via `pi install npm:<package>`, not `pnpm add -g`.

set -eufo pipefail

export PNPM_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/pnpm"
export PATH="$PNPM_HOME/bin:$PATH"

# Packages moved from pnpm globals to pi-managed packages
STALE_PACKAGES=(
    "pi-web-access"
    "pi-subagents"
    "context-mode"
    "pi-intercom"
    "pi-powerline"
    "pi-mcp-adapter"
    "pi-firecrawl"
    "pi-kagi-api"
)

removed=0
for pkg in "${STALE_PACKAGES[@]}"; do
    if pnpm list -g --depth=0 2>/dev/null | grep -q "^${pkg}@"; then
        echo "🗑️  Uninstalling stale global: $pkg"
        pnpm uninstall -g "$pkg" || true
        removed=$((removed + 1))
    else
        echo "✅ $pkg — not installed globally (skip)"
    fi
done

if [[ $removed -gt 0 ]]; then
    echo "🧹 Removed $removed stale pnpm global(s). Install pi packages with:"
    echo "   pi install npm:pi-web-access"
    echo "   pi install npm:pi-subagents"
    echo "   pi install npm:context-mode"
    echo "   pi install npm:pi-intercom"
    echo "   pi install npm:pi-powerline"
    echo "   pi install npm:pi-mcp-adapter"
    echo "   pi install npm:@benvargas/pi-firecrawl"
    echo "   pi install npm:@mjakl/pi-kagi-api"
else
    echo "✅ No stale pnpm globals found."
fi
