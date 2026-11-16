#!/bin/bash
# Remove tmux-agent-panel (and its now-empty tap): agent status in tmux comes
# from tmux-agent-tabs. Declarations were dropped from packages.yaml, mise and
# pi.yaml; this uninstalls the copy brew already put on disk.
set -eufo pipefail

command -v brew >/dev/null || exit 0

if brew list --formula tmux-agent-panel &>/dev/null; then
  brew uninstall tmux-agent-panel
fi
# Fails (harmlessly) if anything else is still installed from the tap.
brew untap ahmedelgabri/tap 2>/dev/null || true
