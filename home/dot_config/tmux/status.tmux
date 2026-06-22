# status.tmux — Status bar configuration for Solarized tmux theme
# This file uses Solarized theme color variables (@thm_*) provided by custom themes
# Designed to match Ghostty's Solarized theme

# Status bar configuration
set-option -g status-position bottom
set-option -g status-justify centre

# Status bar: use theme-defined status colors (purple for Quiet Light, blue for Solarized)
set-option -g status-style "fg=#{@thm_status_fg},bg=#{@thm_status_bg}"

# Window status styling with Solarized colors
set-window-option -g window-status-style "fg=#{@thm_status_fg},bg=#{@thm_status_bg}"
set-window-option -g window-status-current-style "fg=#{@thm_text},bg=#{@thm_surface},bold"
set-window-option -g window-status-bell-style "fg=#{@thm_base},bg=#{@thm_red}"

# Window status format (keep existing format with Pi status integration)
set-window-option -g window-status-format "  #{?@pi-status,#{@pi-status},}#I: #W#{?#{e|>:#{window_panes},1}, (#{window_panes}),}  "
set-window-option -g window-status-current-format "  #{?@pi-status,#{@pi-status},}#I: #W#{?#{e|>:#{window_panes},1}, (#{window_panes}),}  "

# Pane borders using Solarized accent colors
set-option -g pane-border-style "fg=#{@thm_overlay}"
set-option -g pane-active-border-style "fg=#{@thm_blue}"

# Message styling
set-option -g message-style "fg=#{@thm_status_fg},bg=#{@thm_status_bg}"
set-option -g message-command-style "fg=#{@thm_status_fg},bg=#{@thm_status_bg}"

# Copy mode styling  
set-window-option -g mode-style "fg=#{@thm_base},bg=#{@thm_yellow}"

# Status left: UTC time
set-option -g status-left "#[fg=#{@thm_status_fg},bold] UTC #[fg=#{@thm_status_fg},nobold]#(date -u +'%%H:%%M') "

# Status right: local time + timezone
set-option -g status-right "#[fg=#{@thm_status_fg}]%H:%M #[fg=#{@thm_status_fg},bold]%Z "

set-option -g status-left-length 48
set-option -g status-right-length 48

# Window status separator (keep existing spacing)
set-option -g window-status-separator "  "