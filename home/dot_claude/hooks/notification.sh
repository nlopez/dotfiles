#!/usr/bin/env bash
# Sends a macOS notification when Claude needs interaction.
# Clicking the notification switches focus to the tmux window running Claude.
#
# Usage: bash notification.sh [message]
# If no message is given, reads JSON from stdin and uses .message field.

[[ -z "$TMUX" ]] && exit 0
source ~/.claude/hooks/lib/tmux-pane.sh

PANE=$(find_claude_pane) || exit 0

# Fetch SESSION, WINDOW_INDEX, and WINDOW_NAME in a single tmux call
read -r SESSION WINDOW_INDEX WINDOW_NAME < <(tmux display-message -p -t "$PANE" '#{session_name} #{window_index} #{window_name}')
BASE_NAME=$(strip_window_emoji "$WINDOW_NAME")

# Determine notification message
if [[ -n "$1" ]]; then
  MSG="$1"
else
  INPUT=$(cat)
  MSG=$(printf '%s' "$INPUT" | jq -r '.message // "Needs your attention"' 2>/dev/null || echo "Needs your attention")
fi

# Detect running terminal app and return its bundle ID.
# Cached in /tmp for the lifetime of the session to avoid repeated pgrep calls.
detect_terminal_bundle() {
  local cache_file="/tmp/claude_terminal_bundle"
  if [[ -f "$cache_file" ]]; then
    cat "$cache_file"
    return
  fi
  declare -A bundles=(
    [iTerm2]="com.googlecode.iterm2"
    [ghostty]="com.mitchellh.ghostty"
    [kitty]="net.kovidgoyal.kitty"
    [WezTerm]="com.github.wez.wezterm"
    [Terminal]="com.apple.Terminal"
  )
  local bundle="com.apple.Terminal"
  for app in iTerm2 ghostty kitty WezTerm Terminal; do
    if pgrep -xi "$app" > /dev/null 2>&1; then
      bundle="${bundles[$app]}"
      break
    fi
  done
  echo "$bundle" | tee "$cache_file"
}

BUNDLE=$(detect_terminal_bundle)

# Shell command executed when the notification is clicked:
# switch the tmux client to this window, then bring the terminal to front.
CLICK_CMD="tmux switch-client -t '${SESSION}:${WINDOW_INDEX}' 2>/dev/null; open -b '${BUNDLE}'"

if command -v terminal-notifier &>/dev/null; then
  terminal-notifier \
    -title "Claude" \
    -subtitle "$BASE_NAME" \
    -message "$MSG" \
    -activate "$BUNDLE" \
    -execute "$CLICK_CMD" \
    -sound "Glass" \
    -group "claude-${PANE}" \
    > /dev/null 2>&1
else
  osascript -e "display notification \"$MSG\" with title \"Claude\" subtitle \"$BASE_NAME\" sound name \"Glass\""
fi
