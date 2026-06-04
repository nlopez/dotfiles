#!/usr/bin/env bash
# Copy custom Solarized themes to tmux-theme plugin directory
# This runs only when the script content changes

set -euo pipefail

PLUGIN_DIR="$HOME/.config/tmux/plugins/tmux-theme"
CUSTOM_THEMES_DIR="$HOME/.config/tmux/themes"

# Wait for plugins to be installed
sleep 1

# Ensure plugin directory exists
if [ ! -d "$PLUGIN_DIR/themes" ]; then
    echo "tmux-theme plugin not found at $PLUGIN_DIR"
    echo "Please ensure the plugin is installed first."
    exit 1
fi

# Copy our custom Solarized themes to the plugin directory
if [ -f "$CUSTOM_THEMES_DIR/solarized-dark.conf" ] && [ -f "$CUSTOM_THEMES_DIR/solarized-light.conf" ]; then
    echo "Installing custom Solarized themes to tmux-theme plugin..."
    cp "$CUSTOM_THEMES_DIR/solarized-dark.conf" "$PLUGIN_DIR/themes/"
    cp "$CUSTOM_THEMES_DIR/solarized-light.conf" "$PLUGIN_DIR/themes/"
    echo "Solarized themes installed successfully!"
else
    echo "Warning: Custom Solarized theme files not found in $CUSTOM_THEMES_DIR"
fi

# List available themes
echo "Available themes in plugin:"
ls -1 "$PLUGIN_DIR/themes/" | sed 's/\.conf$//' | sort