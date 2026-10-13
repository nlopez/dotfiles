#!/bin/bash

# Install pi-coding-agent via pnpm global so `pi update` works.
# Future upgrades are handled by `pi update`, not chezmoi.
set -eufo pipefail

echo "📦 Installing @earendil-works/pi-coding-agent via pnpm..."
pnpm add -g --ignore-scripts @earendil-works/pi-coding-agent

echo "✅ pi-coding-agent installed ($(pi --version 2>/dev/null || pnpm list -g --depth=0 2>/dev/null | grep pi-coding-agent))"
