#!/bin/bash
# Remap CapsLock → Control on the internal Apple keyboard.
# Runs via hidutil (resets on reboot; the LaunchAgent re-applies it at login).

set -eufo pipefail

PLIST="$HOME/Library/LaunchAgents/com.local.keyremap.plist"

# Reload the LaunchAgent so it is registered with launchd.
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

# Also apply immediately so the remap takes effect without logging out.
/usr/bin/hidutil property \
  --set '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x7000000E0}]}'
