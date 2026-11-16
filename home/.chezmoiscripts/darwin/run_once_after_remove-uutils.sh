#!/bin/bash
# Remove uutils (Rust coreutils/diffutils/findutils) now that GNU tools take
# their place in PATH via gnubin. --ignore-dependencies prevents failures if
# something happened to declare a dep on them.
set -eufo pipefail

for pkg in uutils-coreutils uutils-diffutils uutils-findutils; do
  if brew list --formula "$pkg" &>/dev/null; then
    brew uninstall --ignore-dependencies "$pkg"
  fi
done
