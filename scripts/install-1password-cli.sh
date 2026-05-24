#!/bin/bash
# Install 1Password CLI (op) via rpm-ostree overlay on Fedora Silverblue.
# Must be run BEFORE chezmoi apply, since onepasswordRead templates need `op`.
#
# Usage: sudo ./scripts/install-1password-cli.sh
#
# Note: On Silverblue, rpm-ostree installs require a reboot to take effect.
# Ensure a reboot has occurred after running this before the first `chezmoi apply`.

set -eufo pipefail

SUDO="${SUDO_COMMAND:-sudo}"

# Install 1Password GPG key (idempotent)
if [ ! -f /etc/pki/rpm-gpg/RPM-GPG-KEY-1password ]; then
    echo "Installing 1Password GPG key..."
    curl -fSsL https://downloads.1password.com/linux/keys/1password.asc \
        | $SUDO tee /etc/pki/rpm-gpg/RPM-GPG-KEY-1password > /dev/null
fi

# Add 1Password repo (idempotent - only creates if missing)
if [ ! -f /etc/yum.repos.d/1password.repo ] || ! grep -q '1password' /etc/yum.repos.d/1password.repo; then
    echo "Installing 1Password YUM repository..."
    cat > /tmp/1password.repo << 'EOF'
[1password]
name=1Password Stable Channel
baseurl=https://downloads.1password.com/linux/rpm/stable/$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-1password
EOF
    $SUDO mv /tmp/1password.repo /etc/yum.repos.d/1password.repo
fi

# Install 1password and 1password-cli via rpm-ostree
# This creates a layered overlay on the immutable Silverblue filesystem
$SUDO rpm-ostree install -y 1password 1password-cli
echo ""
echo "DONE: 1Password CLI installed via rpm-ostree."
echo "Note: On Fedora Silverblue, you must reboot for the overlay to take effect."
echo "Run 'systemctl reboot' then re-run 'chezmoi apply' on the next boot."
