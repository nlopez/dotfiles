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

The Connect token lives in the **Private** vault and must be fetched using account-mode `op`
(not Connect mode). Pass it directly to `chezmoi init` via `--promptString` so no interactive
TTY prompt is needed:

```bash
export OP_CONNECT_HOST="https://onepassword-connect.macaroni-pirate.ts.net"
chezmoi init --promptString opConnectToken="$(unset OP_CONNECT_HOST OP_CONNECT_TOKEN; op read op://bamv726zv6zbcfke3cnbwjtnuu/lshy7xejhopza2xq6qpjqlcw5y/credential --no-newline)" --apply nlopez
```

The `unset` subshell is required because `OP_CONNECT_TOKEN` is exported by the generated shell
profile — without it, `op` switches to Connect mode and cannot reach the Private vault.
After `chezmoi apply` completes, the shell profile exports both variables automatically on
every login, so subsequent `chezmoi apply` runs need no manual setup.

For **headless machines**, the same command works. Pre-set `OP_CONNECT_HOST` in the system
environment if preferred (e.g. `/etc/environment`, cloud-init user-data, or a systemd drop-in).

### Notes

- The Connect server is only reachable via Tailscale. Tailscale must be running before
  `chezmoi init` or `chezmoi apply` on any machine.
- **Work machines:** the age encryption key is not in the Automation vault. `fetch-age-key.sh`
  will warn and skip gracefully; encrypted source files will not be decryptable until the age
  identity is provisioned separately.
- To rotate the Connect token: update item `lshy7xejhopza2xq6qpjqlcw5y` in the Private vault,
  then re-run the bootstrap command on each machine (or manually update `opConnectToken` in
  `~/.config/chezmoi/chezmoi.toml` and `[scriptEnv] OP_CONNECT_TOKEN`).
