#!/bin/bash

# Install pi-coding-agent with its own installer (https://pi.dev/install.sh).
# Managed install lives under $PI_CODING_AGENT_DIR/install; upgrades are handled
# by `pi update`, not chezmoi.
set -eufo pipefail

# The old chezmoi-managed shim would block the installer from claiming ~/.local/bin/pi.
if [[ -f "${HOME}/.local/bin/pi" ]] && grep -q 'Shim for pi-coding-agent' "${HOME}/.local/bin/pi"; then
    rm -f "${HOME}/.local/bin/pi"
fi

# The installer has no unattended flag; it skips every prompt (action menu, PATH
# profile edit, "Start pi now?") when /dev/tty can't be opened. Drop the
# controlling terminal with setsid(2) so it runs non-interactively.
echo "📦 Installing pi-coding-agent via pi.dev installer (unattended)..."
curl -fsSL https://pi.dev/install.sh | perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' sh

echo "✅ pi-coding-agent installed ($(pi --version 2>/dev/null || echo 'restart shell to pick up PATH'))"
