#!/bin/bash
# Install 1password and 1password-cli via rpm-ostree (overlay on Fedora Silverblue).
# 1password is not available through brew (Linuxbrew), so we install it as an RPM overlay.
# Based on: https://monospacementor.com/wiki/Notes/Install+1Password+on+Fedora+Silverblue

set -eufo pipefail

SUDO="${SUDO_COMMAND:-sudo}"

# Install 1Password GPG key (idempotent)
if [ ! -f /etc/pki/rpm-gpg/RPM-GPG-KEY-1password ]; then
    echo "Installing 1Password GPG key..."
    curl -fSsL https://downloads.1password.com/linux/keys/1password.asc \
        | $SUDO tee /etc/pki/rpm-gpg/RPM-GPG-KEY-1password > /dev/null
fi

# Add 1Password repo (idempotent - only updates if changed)
REPO_CONTENT='[1password]
name=1Password Stable Channel
baseurl=https://downloads.1password.com/linux/rpm/stable/$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-1password'

if [ ! -f /etc/yum.repos.d/1password.repo ] || ! grep -q '1password' /etc/yum.repos.d/1password.repo; then
    echo "Installing 1Password YUM repository..."
    echo "$REPO_CONTENT" | $SUDO tee /etc/yum.repos.d/1password.repo > /dev/null
fi

# Install 1password and 1password-cli via rpm-ostree
# This creates a layered overlay on the immutable Silverblue filesystem
$SUDO rpm-ostree install -y 1password 1password-cli
