#!/bin/sh
# Remove atuin self-installer artifacts now that atuin is managed by homebrew.
# The database lives in ~/.local/share/atuin/ and is unaffected.

# Self-installed binary + logs
rm -rf "$HOME/.atuin"

