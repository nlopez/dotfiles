#!/usr/bin/env bash
# Install Nix via the Determinate Nix installer.
# https://determinate.systems/nix
#
# Skips if Nix is already installed. Runs before dotfiles are written so
# that nix is available for any subsequent run_after_ scripts that need it.

set -eufo pipefail

if [ -e /nix ] || command -v nix &>/dev/null; then
    echo "[install-nix] Nix already installed, skipping."
    exit 0
fi

echo "[install-nix] Installing Nix via Determinate Nix installer..."
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix \
    | sh -s -- install --no-confirm

echo "[install-nix] Done. Open a new shell to use nix."
