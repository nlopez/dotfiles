#!/bin/bash
# Install 1password and 1password-cli via rpm-ostree (overlay on Fedora Silverblue).
# 1password is not available through brew (Linuxbrew), so we install it as an RPM overlay.
# Based on: https://leopoldluley.de/posts/install-1password-with-rpm-ostree/

set -eufo pipefail

rpm-ostree install -y 1password 1password-cli
