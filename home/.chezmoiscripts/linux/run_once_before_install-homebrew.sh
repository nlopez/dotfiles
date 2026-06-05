#!/bin/bash
# Install Homebrew (Linuxbrew) if not already installed.
# Based on: https://brew.sh/
#
# This script runs BEFORE run_onchange_before_install-packages-brew.sh.tmpl
# because "once" sorts lexicographically before "onchange".

set -eufo pipefail

if command -v brew &>/dev/null; then
  echo "Homebrew already installed, skipping."
  exit 0
fi

# Install build dependencies
if command -v apt-get &>/dev/null; then
  sudo apt-get update -q
  sudo apt-get install -y build-essential procps curl file git
elif command -v dnf &>/dev/null; then
  sudo dnf groupinstall -y 'Development Tools'
  sudo dnf install -y procps-ng curl file git
fi

# Install Homebrew non-interactively
NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
