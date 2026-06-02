#!/bin/sh
# Reload tmux config if tmux is running
if tmux info >/dev/null 2>&1; then
    tmux source-file "$HOME/.config/tmux/tmux.conf" >/dev/null 2>&1 || true
fi
