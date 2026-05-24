#!/bin/bash
# Uninstall Zed — reverses what install-zed.sh does.

set -eufo pipefail

ZED_BIN="$HOME/.local/bin/zed"
ZED_APPS="$HOME/.local/share/applications"

# Remove symlink
if [ -L "$ZED_BIN" ] || [ -f "$ZED_BIN" ]; then
    rm -f "$ZED_BIN"
fi

# Remove .desktop files for all channels
for appid in dev.zed.Zed dev.zed.Zed-Nightly dev.zed.Zed-Preview dev.zed.Zed-Dev; do
    rm -f "$ZED_APPS/${appid}.desktop"
done

# Remove app directories
for suffix in "" "-nightly" "-preview" "-dev"; do
    rm -rf "$HOME/.local/zed${suffix}.app"
done

echo "Zed has been uninstalled."
