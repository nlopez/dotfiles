#!/bin/sh
# Remove atuin self-installer artifacts now that atuin is managed by homebrew.
# The database lives in ~/.local/share/atuin/ and is unaffected.

# Self-installed binary + logs
rm -rf "$HOME/.atuin"

# Remove ~/.atuin/bin from fish's persistent $fish_user_paths universal variable
if command -v fish >/dev/null 2>&1; then
  fish -c '
    set -l clean
    for p in $fish_user_paths
      if test "$p" != "$HOME/.atuin/bin"
        set -a clean $p
      end
    end
    set -U fish_user_paths $clean
  '
fi
