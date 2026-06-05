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
set-window-option -g window-status-format "  #{?@pi-status,#{@pi-status},}#I: #W#{?#{e|>:#{window_panes},1}, (#{window_panes}),}  "
set-window-option -g window-status-current-format "  #{?@pi-status,#{@pi-status},}#I: #W#{?#{e|>:#{window_panes},1}, (#{window_panes}),}  "

# Pane borders using Solarized accent colors
set-option -g pane-border-style "fg=#{@thm_overlay}"
set-option -g pane-active-border-style "fg=#{@thm_blue}"

# Message styling with Solarized blue accent
set-option -g message-style "fg=#{@thm_base},bg=#{@thm_blue}"
set-option -g message-command-style "fg=#{@thm_base},bg=#{@thm_cyan}"

# Copy mode styling  
set-window-option -g mode-style "fg=#{@thm_base},bg=#{@thm_yellow}"

# Status left: UTC time (uses `date -u`; %% is escaped so tmux passes the
# strftime directives through to date instead of expanding them as local time)
set-option -g status-left "#[fg=#{@thm_cyan},bold] UTC #[fg=#{@thm_text},nobold]#(date -u +'%%H:%%M') "

# Status right: local time + timezone (tmux native strftime = local time)
set-option -g status-right "#[fg=#{@thm_text}]%H:%M #[fg=#{@thm_cyan},bold]%Z "

set-option -g status-left-length 48
set-option -g status-right-length 48

# Window status separator (keep existing spacing)
set-option -g window-status-separator "  "