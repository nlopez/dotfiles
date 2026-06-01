# Setup

```
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password Connect

All secrets are read via a self-hosted [1Password Connect](https://developer.1password.com/docs/connect/)
server reachable over Tailscale at `onepassword-connect.macaroni-pirate.ts.net`. The Connect
token is scoped to the `Automation` vault, where all chezmoi-managed secrets live.

chezmoi is configured with `onepassword.mode = "connect"`. The `OP_CONNECT_HOST` and
`OP_CONNECT_TOKEN` environment variables must be set before chezmoi can read any secrets.

### Bootstrap (first run on any machine)

Obtain the Connect token from 1Password and export it before running chezmoi:

```bash
export OP_CONNECT_HOST="https://onepassword-connect.macaroni-pirate.ts.net"
export OP_CONNECT_TOKEN="$(op read op://Private/lshy7xejhopza2xq6qpjqlcw5y/credential --no-newline)"
```

Then run chezmoi normally. On first run, `chezmoi init` will prompt for the Connect token
via `promptStringOnce` — paste the same value. After `chezmoi apply` completes, your shell
profile will export both variables automatically on every login, so subsequent runs need no
manual setup.

For **headless machines**, pre-set `OP_CONNECT_HOST` and `OP_CONNECT_TOKEN` in the system
environment (e.g. `/etc/environment`, cloud-init user-data, or a systemd drop-in) before
running chezmoi.

### Migrating an existing machine

If you have a machine already running this chezmoi config from before the Connect migration,
re-run `chezmoi init` to trigger the `promptStringOnce` prompt for the token:

```bash
export OP_CONNECT_HOST="https://onepassword-connect.macaroni-pirate.ts.net"
export OP_CONNECT_TOKEN="$(op read op://Private/lshy7xejhopza2xq6qpjqlcw5y/credential --no-newline)"
chezmoi init nlopez   # prompts for opConnectToken — paste the token value
chezmoi apply
```

### Notes

- The Connect server is only reachable via Tailscale. Tailscale must be running before
  `chezmoi apply` on any machine.
- **Work machines:** the age encryption key is not in the Automation vault. `fetch-age-key.sh`
  will warn and skip gracefully; encrypted source files will not be decryptable until the age
  identity is provisioned separately.
- To rotate the Connect token: update `op://Private/lshy7xejhopza2xq6qpjqlcw5y/credential`
  in 1Password, then re-run `chezmoi init` on each machine (or manually edit
  `~/.config/chezmoi/chezmoi.toml` to update `opConnectToken`).
