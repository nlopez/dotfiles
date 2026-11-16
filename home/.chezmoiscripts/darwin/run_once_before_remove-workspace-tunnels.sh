#!/bin/bash

# Unload the retired workspace-tunnels supervisor and its per-workspace tunnel
# jobs before .chezmoiremove deletes their plists. Workspace tunnels are now
# managed by `workspaces rex tunnels`.

set -uo pipefail

DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/com.local.workspace-tunnels" 2>/dev/null || true
for label in $(launchctl list | awk 'index($3, "com.local.workspace-tunnel.") == 1 { print $3 }'); do
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
done
exit 0
