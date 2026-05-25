#!/bin/bash

# Remove Homebrew rclone (lacks FUSE mount support on macOS)
# Triggered automatically when rclone is removed from brews.base in packages.yaml
set -eufo pipefail

if brew list --formula 2>/dev/null | grep -q '^rclone$'; then
    echo "🗑️  Removing Homebrew rclone (lacks mount support)..."
    brew uninstall rclone
fi

# Clean up stale manual-install binary from /usr/local/bin
if [[ -f /usr/local/bin/rclone ]]; then
    echo "🗑️  Removing stale /usr/local/bin/rclone..."
    sudo rm -f /usr/local/bin/rclone
fi

echo "✅ rclone cleanup complete (new binary from chezmoi external at ~/.local/bin/rclone)"
