#!/bin/bash
# Configure the 1Password YUM/DNF repository.
# Based on: https://leopoldluley.de/posts/install-1password-with-rpm-ostree/
# Both 1password (GUI) and 1password-cli are installed via rpm-ostree in
# run_onchange_before_install-packages-dnf.sh.tmpl.

set -eufo pipefail

# Import the 1Password public GPG key
sudo rpm --import https://downloads.1password.com/linux/keys/1password.asc

# Add the 1Password stable repository configuration
sudo sh -c 'echo -e "[1password]\nname=1Password Stable Channel\nbaseurl=https://downloads.1password.com/linux/rpm/stable/\$basearch\nenabled=1\ngpgcheck=1\nrepo_gpgcheck=1\ngpgkey=\"https://downloads.1password.com/linux/keys/1password.asc\"" > /etc/yum.repos.d/1password.repo'
