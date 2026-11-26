#!/bin/bash

# Rex (Superlogical) ships only as a DMG, with no cask or nixpkg. Install it once
# if it's missing; after that the app's own updater (Sparkle) keeps it current.

set -euo pipefail

APP=/Applications/Rex.app
URL=https://blob.superlogical.com/download/rex-app/preview/latest.dmg
TEAM=AG92C3PT77

[ -d "$APP" ] && exit 0

tmp="$(mktemp -d)"
mnt="$tmp/mnt"
cleanup() {
  hdiutil detach -quiet "$mnt" 2>/dev/null || true
  trash "$tmp" 2>/dev/null || true
}
trap cleanup EXIT

echo "rex: downloading $URL"
curl -fsSL -o "$tmp/rex.dmg" "$URL"
hdiutil attach -quiet -nobrowse -readonly -mountpoint "$mnt" "$tmp/rex.dmg"

if ! codesign -dv "$mnt/Rex.app" 2>&1 | grep -qx "TeamIdentifier=$TEAM"; then
  echo "rex: unexpected signer on $mnt/Rex.app, not installing" >&2
  exit 1
fi
spctl -a "$mnt/Rex.app"

ditto "$mnt/Rex.app" "$APP"
echo "rex: installed $APP"
