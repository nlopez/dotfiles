#!/usr/bin/env bash
# Print a rich color palette with names formatted for tmux config files.
# Usage: tmux-colors [256]   # default is 16 colors, pass "256" for full palette

set -euo pipefail

count=${1:-16}

printf "%-30s %-12s %s\n" "NAME" "TMUX" "COLOR"
printf "%s\n" "$(printf '=%.0s' {1..60})"

# 16 standard ANSI colors
names=(
  black     red       green     yellow
  blue      magenta   cyan      white
  brblack   brred     brgreen   bryellow
  brblue    brmagenta brcyan    brwhite
)

for i in $(seq 0 $(( count > 16 ? 15 : count - 1 ))); do
  name=${names[$i]}
  printf "  \033[${i}m %-30s  colour${i}  [ESC [${i}m   \033[0m\n" "$name"
done

if (( count > 16 )); then
  printf "\n%s\n" "$(printf '=%.0s' {1..60})"
  printf "%-30s %-12s %s\n" "NAME" "TMUX" "COLOR"
  printf "%s\n" "$(printf '=%.0s' {1..60})"

  # 256-color extended palette: 6×6×6 color cube
  cube_red=(0 95 135 175 215 235)
  cube_green=(0 119 127 151 191 231)
  cube_blue=(0 71 111 151 191 239)
  gray=(8 16 22 28 34 40 46 52 58 64 70 76 82 88 94 100 106 112 118 124 130 136 142 148 154)

  idx=0
  for r in "${cube_red[@]}"; do
    for g in "${cube_green[@]}"; do
      for b in "${cube_blue[@]}"; do
        if (( idx > 255 )); then break 3; fi
        if (( idx < 16 )); then idx=$((idx + 1)); continue; fi
        printf "  \033[38;5;%dm  %-30s  colour%d  [RGB %d,%d,%d]\033[0m\n" \
          "$idx" "color${idx}" "$idx" "$r" "$g" "$b"
        idx=$((idx + 1))
      done
    done
  done

  for g in "${gray[@]}"; do
    if (( idx > 255 )); then break; fi
    printf "  \033[38;5;%dm  %-30s  colour%d  [Gray %d]\033[0m\n" \
      "$idx" "gray${idx}" "$idx" "$g"
    idx=$((idx + 1))
  done
fi

printf "\n%s\n" "$(printf '=%.0s' {1..60})"
printf "\nTmux usage examples:\n"
printf "  \033[38;5;208m# Colour208 fg \033[0m  set -g status-bg 'colour237'\n"
printf "  \033[38;5;118m# Colour118 fg \033[0m  set -g pane-border-fg 'colour0'\n"
printf "\nTo see more detail on a specific color:\n"
printf "  tmux-colors 256 | grep colour<N>\n"
