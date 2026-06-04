#!/usr/bin/env bash
# Install tmux plugins using TPM
# This runs only when the script content changes (not on every chezmoi apply)

set -euo pipefail

TPM_DIR="$HOME/.config/tmux/plugins/tpm"
TMUX_PLUGINS_CMD="$HOME/.local/bin/tmux-plugins"

# Wait a moment for external sources to be processed
sleep 2

# Ensure TPM is installed, or install it manually
if [ ! -d "$TPM_DIR" ]; then
    echo "TPM not found, installing manually..."
    mkdir -p "$(dirname "$TPM_DIR")"
    git clone https://github.com/tmux-plugins/tpm "$TPM_DIR"
fi

# Use our wrapper script for plugin management
if [ -x "$TMUX_PLUGINS_CMD" ]; then
    echo "Installing tmux plugins..."
    "$TMUX_PLUGINS_CMD" install
else
    echo "tmux-plugins command not found, using TPM directly..."
    # Make TPM script executable
    chmod +x "$TPM_DIR/bin/install_plugins"
    
    # Start a temporary tmux session to install plugins
    tmux new-session -d -s tpm_install 2>/dev/null || true
    sleep 1
    tmux send-keys -t tpm_install "$TPM_DIR/bin/install_plugins" C-m 2>/dev/null || true
    sleep 3
    tmux kill-session -t tpm_install 2>/dev/null || true
fi

echo "Tmux plugins installation complete!"
echo "Note: Reload tmux or restart tmux sessions to see changes."

# If tmux is running, optionally reload configuration
if pgrep tmux > /dev/null; then
    echo "Tmux is running. You can reload configuration with:"
    echo "  tmux source-file ~/.config/tmux/tmux.conf"
fi