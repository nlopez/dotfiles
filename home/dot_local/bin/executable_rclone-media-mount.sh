#!/bin/sh
set -eu

export PATH="{{ .chezmoi.homeDir }}/.local/bin:{{ .packages.brew_prefix }}/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export RCLONE_CONFIG="{{ .chezmoi.homeDir }}/.config/rclone/rclone.conf"
export HOME="{{ .chezmoi.homeDir }}"

MOUNT_DIR="{{ .chezmoi.homeDir }}/mnt/media"

if [ ! -d "$MOUNT_DIR" ]; then
    mkdir -p "$MOUNT_DIR"
fi

exec {{ .chezmoi.homeDir }}/.local/bin/rclone mount media: "$MOUNT_DIR" \
    --allow-other \
    --log-level INFO \
    --log-file "{{ .chezmoi.homeDir }}/Library/Logs/rclone-media-mount.log" \
    --rc \
    --rc-addr localhost:5572 \
    --rc-no-auth
