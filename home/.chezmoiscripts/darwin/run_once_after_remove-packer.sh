#!/bin/bash
# Remove packer (and the hashicorp tap) now that it is no longer declared in
# packages.yaml or mise.
set -eufo pipefail

command -v brew >/dev/null || exit 0

if brew list --formula packer &>/dev/null; then
  brew uninstall packer
fi
# Fails (harmlessly) if anything else is still installed from the tap.
brew untap hashicorp/tap 2>/dev/null || true
