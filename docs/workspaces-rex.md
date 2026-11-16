# Rex on cloud workspaces

[Rex](https://www.superlogical.com/rex) keeps terminals and agents running on a
workspace while the laptop is closed. These dotfiles install the Rex server on
every workspace, and a supervisor on work Macs keeps tunnels to them.

| Source file                                                                | Where     | Role                                                  |
| -------------------------------------------------------------------------- | --------- | ----------------------------------------------------- |
| `home/.chezmoidata/rex.yaml`                                               | —         | Pinned Rex release: version, commit, sha256 per arch  |
| `home/.chezmoiscripts/linux/run_onchange_after_50-rex-server.sh.tmpl`      | workspace | Installs `~/.local/bin/rex` and starts the server     |
| `home/dot_local/share/workspaces-rex/executable_ensure.tmpl`               | workspace | Starts the server if needed; keeps the crontab entry  |
| `home/dot_local/bin/executable_workspaces-rex.tmpl`                        | work Mac  | Tunnel supervisor and `status` (Python, run by `uv`)  |
| `home/Library/LaunchAgents/com.local.workspaces-rex.plist.tmpl`            | work Mac  | Runs `workspaces-rex supervise` at login              |
| `home/.chezmoiscripts/darwin/run_onchange_after_20-workspaces-rex.sh.tmpl` | work Mac  | Reloads the supervisor when it changes                |
| `home/dot_config/rex/init.lua`                                             | all       | Loads the generated `workspaces_rex.lua` hosts module |

## Setup

1. New workspaces get the server when dotfiles apply at creation. Nothing to do.
2. Within a minute, the Mac gets a socket per running workspace at
   `~/.local/state/workspaces/rex/<workspace>.sock`.
3. In Rex for Mac, open Settings > Remote Hosts and add a remote host with the
   full path (no `~`) of that socket. This is the only manual step.

## Check status

```sh
workspaces-rex status
```

- `REX SOCKET listening`: Rex for Mac can connect to the workspace.
- `SSH AGENT forwarded`: terminals on the workspace can use this Mac's SSH keys.
  The supervisor forwards the agent only while a Rex client is connected, so an
  idle workspace can still pause.

The supervisor log is `~/.local/state/workspaces/rex/supervisor.log`.

## Bump Rex

1. Read `https://blob.superlogical.com/api/releases/rex/<channel>` (`stable`
   returns 404 until Rex has a stable release; use `preview`).
2. Copy `version`, `commit` and the `sha256` of `rex-linux-amd64.tar.gz` and
   `rex-linux-arm64.tar.gz` into `home/.chezmoidata/rex.yaml`.
3. `chezmoi apply` on each workspace installs the new binary. A running server
   keeps its version until it stops, because stopping it ends its sessions. To
   switch now: `rex --autostart=false server stop && ~/.local/share/workspaces-rex/ensure`.

## How it works

- On the workspace, Rex runs as your user and listens only on its Unix socket.
  The tarball is checked against the pinned sha256. A crontab block
  (`# BEGIN workspaces-rex`) runs `ensure` every minute to restart the server.
- On the Mac, the supervisor polls `workspaces list` every minute. For each
  `PROVISIONED` workspace it runs `ensure` over ssh, which also reports the
  server's socket. It bootstraps a socket-activated launchd job
  (`com.local.workspaces-rex.tunnel.<workspace>`) that runs `ssh -W` to that
  socket for each connection. Paused workspaces get no socket, so Rex does not
  resume them.
- While a tunnel has a connection, an agent-holder job
  (`com.local.workspaces-rex.agent.<workspace>`) keeps one `ForwardAgent=yes`
  session open.
- After the Mac wakes, the supervisor closes the ssh connection masters so
  launchd reconnects at once.
- The tunnel jobs keep running when the supervisor restarts; the new supervisor
  adopts each job whose plist is unchanged.
