#!/bin/bash

# Remove Homebrew dark-notify and its tap; nothing in this repo uses it anymore
# (the dark-notify-tmux LaunchAgent was retired, see .chezmoiremove).
set -eufo pipefail

command -v brew >/dev/null || exit 0

if brew list --formula 2>/dev/null | grep -q '^dark-notify$'; then
    echo "🗑️  Removing Homebrew dark-notify..."
    brew uninstall dark-notify
fi

if brew tap 2>/dev/null | grep -q '^cormacrelf/tap$'; then
    echo "🗑️  Removing cormacrelf/tap..."
    brew untap cormacrelf/tap
fi

echo "✅ dark-notify removed"
