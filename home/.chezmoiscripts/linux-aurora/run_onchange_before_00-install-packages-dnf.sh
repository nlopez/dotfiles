#!/bin/bash
# Configure the 1Password CLI YUM/DNF repository.
# Aurora Linux (OSTree) has a read-only /usr — cannot use rpm --import.
# Workaround: write GPG key to /etc/pki/rpm-gpg/ and reference via file:// in repo.
# Based on: https://monospacementor.com/wiki/Notes/Install+1Password+on+Fedora+Silverblue

set -eufo pipefail

# Write the 1Password public GPG key to the writable overlay
mkdir -p /etc/pki/rpm-gpg
curl -sSf https://downloads.1password.com/linux/keys/1password.asc \
  | tee /etc/pki/rpm-gpg/RPM-GPG-KEY-1password > /dev/null

# Add the 1Password stable repository configuration
# Uses file:// gpgkey since /usr/share/rpm/ is read-only on OSTree
sh -c 'echo -e "[1password]\nname=1Password Stable Channel\nbaseurl=https://downloads.1password.com/linux/rpm/stable/\$basearch\nenabled=1\ngpgcheck=1\nrepo_gpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-1password" > /etc/yum.repos.d/1password.repo'
