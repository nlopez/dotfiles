# status.tmux — Status bar configuration for Solarized tmux theme
# This file uses Solarized theme color variables (@thm_*) provided by custom themes
# Designed to match Ghostty's Solarized theme

# Status bar configuration
set-option -g status-position bottom
set-option -g status-justify centre

# Use Solarized theme variables for status bar colors
set-option -g status-style "fg=#{@thm_subtle},bg=#{@thm_base}"

# Window status styling with Solarized colors
set-window-option -g window-status-style "fg=#{@thm_muted},bg=#{@thm_base}"
set-window-option -g window-status-current-style "fg=#{@thm_text},bg=#{@thm_surface},bold"
set-window-option -g window-status-bell-style "fg=#{@thm_base},bg=#{@thm_red}"

# Window status format (keep existing format with Pi status integration)
set-window-option -g window-status-format "  #{?@pi-status,#{@pi-status},}#I: #W  "
set-window-option -g window-status-current-format "  #{?@pi-status,#{@pi-status},}#I: #W  "

# Pane borders using Solarized accent colors
set-option -g pane-border-style "fg=#{@thm_overlay}"
set-option -g pane-active-border-style "fg=#{@thm_blue}"

# Message styling with Solarized blue accent
set-option -g message-style "fg=#{@thm_base},bg=#{@thm_blue}"
set-option -g message-command-style "fg=#{@thm_base},bg=#{@thm_cyan}"

# Copy mode styling  
set-window-option -g mode-style "fg=#{@thm_base},bg=#{@thm_yellow}"

# Status left and right (empty to match existing config)
set-option -g status-left ""
set-option -g status-right ""
set-option -g status-left-length 48

# Window status separator (keep existing spacing)
set-option -g window-status-separator "  "