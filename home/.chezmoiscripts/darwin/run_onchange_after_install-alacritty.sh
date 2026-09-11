#!/bin/bash
# Install Alacritty from GitHub Releases (Homebrew cask is disabled due to Gatekeeper)
# renovate: datasource=github-releases depName=alacritty/alacritty
ALACRITTY_VERSION="v0.17.0"

set -euo pipefail

APP="/Applications/Alacritty.app"
DMG_URL="https://github.com/alacritty/alacritty/releases/download/${ALACRITTY_VERSION}/Alacritty-${ALACRITTY_VERSION}.dmg"
TMP_DMG=$(mktemp /tmp/alacritty-XXXXXX.dmg)
MOUNT_POINT=$(mktemp -d /tmp/alacritty-mount-XXXXXX)

cleanup() {
  hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
  rm -f "$TMP_DMG"
  rmdir "$MOUNT_POINT" 2>/dev/null || true
}
trap cleanup EXIT

# Check if already at this version
if [[ -d "$APP" ]]; then
  installed=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$APP/Contents/Info.plist" 2>/dev/null || echo "")
  if [[ "$installed" == "${ALACRITTY_VERSION#v}" ]]; then
    echo "Alacritty ${ALACRITTY_VERSION} already installed, skipping."
    exit 0
  fi
fi

echo "Installing Alacritty ${ALACRITTY_VERSION}..."
curl -fsSL "$DMG_URL" -o "$TMP_DMG"
hdiutil attach "$TMP_DMG" -mountpoint "$MOUNT_POINT" -nobrowse -quiet
[[ -d "$APP" ]] && rm -rf "$APP"
cp -R "$MOUNT_POINT/Alacritty.app" /Applications/
xattr -dr com.apple.quarantine "$APP"
echo "Alacritty ${ALACRITTY_VERSION} installed."
