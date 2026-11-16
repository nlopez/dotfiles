#!/bin/bash
# One-time repair of stale Homebrew state:
#  - libkrun was installed against the old libkrun/krun/virglrenderer formula,
#    which the tap renamed to virglrenderer-krun.
#  - libtiff/webp have stale keg-tab dependency data (circular dependency).
set -eufo pipefail

command -v brew >/dev/null || exit 0

brew update --quiet || true

if brew list --formula libtiff &>/dev/null || brew list --formula webp &>/dev/null; then
  brew uninstall --ignore-dependencies --force libtiff webp || true
  brew install libtiff webp
fi

if brew list --formula virglrenderer &>/dev/null; then
  brew uninstall --ignore-dependencies --force virglrenderer || true
fi
if brew list --formula libkrun &>/dev/null; then
  brew reinstall libkrun/krun/libkrun libkrun/krun/krunkit
fi
