#!/bin/bash
# Install 1Password desktop app and 1Password CLI on Ubuntu/Debian.
# Based on: https://support.1password.com/install-linux/#debian-or-ubuntu
#
# Skips gracefully on non-Debian/Ubuntu systems (e.g. Aurora/Fedora).
# Both packages come from the same official 1Password apt repository:
#   1password      — desktop app + SSH agent (/opt/1Password/op-ssh-sign)
#   1password-cli  — op command-line tool

set -eufo pipefail

# Only run on Debian/Ubuntu systems
if ! command -v apt-get &>/dev/null; then
  echo "Not a Debian/Ubuntu system, skipping 1Password install."
  exit 0
fi

# Skip if already fully installed
if dpkg -s 1password &>/dev/null 2>&1 && dpkg -s 1password-cli &>/dev/null 2>&1; then
  echo "1Password and 1Password CLI already installed, skipping."
  exit 0
fi

# 1. Add the GPG key for the 1Password apt repository
sudo mkdir -p /usr/share/keyrings
curl -sS https://downloads.1password.com/linux/keys/1password.asc \
  | sudo gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg

# 2. Add the 1Password apt repository
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main' \
  | sudo tee /etc/apt/sources.list.d/1password.list

# 3. Add the debsig-verify policy (package signature verification)
sudo mkdir -p /etc/debsig/policies/AC2D62742012EA22/
curl -sS https://downloads.1password.com/linux/debian/debsig/1password.pol \
  | sudo tee /etc/debsig/policies/AC2D62742012EA22/1password.pol
sudo mkdir -p /usr/share/debsig/keyrings/AC2D62742012EA22
curl -sS https://downloads.1password.com/linux/keys/1password.asc \
  | sudo gpg --dearmor --output /usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg

# 4. Install 1Password and 1Password CLI
sudo apt-get update -q
sudo apt-get install -y 1password 1password-cli
