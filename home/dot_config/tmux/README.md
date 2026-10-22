# Tmux Configuration

This directory contains the tmux configuration managed by chezmoi.

## Setup

The configuration includes:

- **TPM (Tmux Plugin Manager)**: Automatically installed via chezmoi external sources
- **tmux-contrib/tmux-theme**: Auto-switching theme plugin with custom themes (Solarized Dark / Quiet Light, matching Ghostty)
- **jhickner/tmux-agent-tabs**: Agent status markers in window tabs (colors set per theme)
- **tmux-resurrect / tmux-continuum**: Session save and restore
- **tap** (`prefix + g`): agent-aware pane picker
- Custom key bindings and status bar configuration
- Automatic light/dark mode detection using tmux 3.5+ hooks

## Plugin Management

### Automatic Installation

Plugins are automatically installed when you run:

```bash
chezmoi apply
```

### Manual Management

Use the `tmux-plugins` command for manual plugin management:

```bash
# Install all plugins
tmux-plugins install

# Update all plugins
tmux-plugins update

# Clean unused plugins
tmux-plugins clean

# List installed plugins
tmux-plugins list
```

### TPM Key Bindings

Once TPM is installed, you can use these key bindings within tmux:

- `prefix + I` (shift + i) - Install new plugins
- `prefix + U` - Update installed plugins
- `prefix + alt + u` - Uninstall plugins not in config

## Configuration

### Theme Settings

The tmux-theme plugin is configured with custom themes in `themes/`:

- `@theme-dark 'solarized-dark'` - Solarized Dark (matches Ghostty)
- `@theme-light 'quiet-light'` - Quiet Light (matches Ghostty)
- `solarized-light` is also available
- Each theme defines `@thm_*` colors and the `@agent_tabs_color_*` markers
- Automatic switching based on system appearance
- `status.tmux` is sourced after the theme and applies the status bar styling

### Adding New Plugins

To add new plugins:

1. Edit `~/.config/tmux/tmux.conf` (via `chezmoi edit ~/.config/tmux/tmux.conf`)
2. Add the plugin line: `set -g @plugin 'user/plugin-name'`
3. Run `tmux-plugins install` or `prefix + I` in tmux

### Files

- `tmux.conf` - Main tmux configuration with plugin setup
- `status.tmux` - Status bar styling (uses theme colors)
- `themes/` - Custom theme color definitions
- `scripts/` - Helper scripts (`pane-cmd.sh`, `rename-window.sh`)
- `plugins/` - Plugin directory (managed by TPM)
  - `tpm/` - Tmux Plugin Manager
  - `tmux-theme/`, `tmux-agent-tabs/`, `tmux-resurrect/`, `tmux-continuum/`

## Automatic Theme Switching

The tmux-contrib/tmux-theme plugin automatically detects your system's light/dark mode using tmux 3.5+ `client-dark-theme` and `client-light-theme` hooks. When you change your system appearance, tmux will instantly switch between the dark and light themes to match your Ghostty terminal.

**How it works:**

- Plugin uses native tmux theme detection (tmux 3.5+ hooks)
- Custom themes installed during chezmoi apply
- Color consistency with Ghostty themes
- No external dependencies or background processes needed
- Instant switching when system appearance changes
- Works with all modern terminals that support CSI 2031 (Ghostty, Kitty, WezTerm, etc.)

## Troubleshooting

If plugins aren't working:

1. Ensure TPM is installed: `ls ~/.config/tmux/plugins/tpm`
2. Ensure tmux-theme is installed: `ls ~/.config/tmux/plugins/tmux-theme`
3. Reload tmux config: `tmux source-file ~/.config/tmux/tmux.conf`
4. Install plugins: `tmux-plugins install`
5. Restart tmux sessions if needed

If themes aren't switching:

1. Ensure you're using tmux 3.5+ with a supported terminal
2. Test theme switching: change your system appearance and check if tmux updates
3. Check if your terminal supports CSI 2031 (most modern terminals do)
4. Verify the plugin is loaded: `tmux show-environment -g | grep TMUX_PLUGIN`
