#!/usr/bin/env bash
# install-op.sh — Installs the 1Password CLI when it is missing.
#
# fetch-age-key.sh needs `op` before chezmoi reads (and decrypts) source state,
# which is earlier than the Nix profile that normally provides it, so the CLI has
# to come from Homebrew (macOS) or the official apt repository (Debian/Ubuntu).
set -euo pipefail

if command -v op >/dev/null; then
    exit 0
fi

case "$(uname -s)" in
Darwin)
    if ! command -v brew >/dev/null; then
        echo "install-op: installing Homebrew" >&2
        NONINTERACTIVE=1 /bin/bash -c \
            "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true
        for prefix in /opt/homebrew /usr/local; do
            if [[ -x "${prefix}/bin/brew" ]]; then
                eval "$("${prefix}/bin/brew" shellenv)"
                break
            fi
        done
    fi
    if command -v brew >/dev/null; then
        HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ENV_HINTS=1 brew install --cask 1password-cli
    fi
    ;;
Linux)
    if ! command -v apt-get >/dev/null; then
        echo "install-op: not a Debian/Ubuntu system, install 1password-cli with your package manager" >&2
        exit 1
    fi
    # https://support.1password.com/install-linux/#debian-or-ubuntu
    if [[ ! -s /usr/share/keyrings/1password-archive-keyring.gpg ]]; then
        sudo mkdir -p /usr/share/keyrings
        curl -sS https://downloads.1password.com/linux/keys/1password.asc |
            sudo gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg
        echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main' |
            sudo tee /etc/apt/sources.list.d/1password.list
        sudo mkdir -p /etc/debsig/policies/AC2D62742012EA22/
        curl -sS https://downloads.1password.com/linux/debian/debsig/1password.pol |
            sudo tee /etc/debsig/policies/AC2D62742012EA22/1password.pol
        sudo mkdir -p /usr/share/debsig/keyrings/AC2D62742012EA22
        curl -sS https://downloads.1password.com/linux/keys/1password.asc |
            sudo gpg --dearmor --output /usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg
    fi
    sudo apt-get update -q
    sudo apt-get install -y 1password-cli
    ;;
*)
    echo "install-op: unsupported OS $(uname -s)" >&2
    exit 1
    ;;
esac

if ! command -v op >/dev/null; then
    echo "install-op: ERROR — could not install the 1Password CLI (op)." >&2
    echo "  macOS: brew install --cask 1password-cli" >&2
    echo "  Other: https://developer.1password.com/docs/cli/get-started" >&2
    exit 1
fi
