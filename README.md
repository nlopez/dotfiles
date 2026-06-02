# Setup

```
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password Connect

All secrets are read via a self-hosted [1Password Connect](https://developer.1password.com/docs/connect/)
server reachable over Tailscale at `onepassword-connect.macaroni-pirate.ts.net`. The Connect
token is scoped to the `Automation` vault, where all chezmoi-managed secrets live.

chezmoi is configured with `onepassword.mode = "connect"`.
On macOS, `OP_CONNECT_HOST` and `OP_CONNECT_TOKEN` are set by `~/.zprofile` at login —
`OP_CONNECT_TOKEN` is fetched from Keychain at runtime so it never appears in any
chezmoi-managed file. On headless machines they are set via the bootstrap command.

### Bootstrap (first run on any machine)

The Connect token lives in the **Private** vault and must be fetched using account-mode `op`
(not Connect mode). Use the included bootstrap script:

```bash
~/.local/bin/bootstrap-op-connect-token --apply
```

This fetches the token from `op://Private/OP_CONNECT_TOKEN/credential` (unsetting
`OP_CONNECT_HOST`/`OP_CONNECT_TOKEN` so `op` uses account mode), stores it in macOS
Keychain, then runs `chezmoi init --apply nlopez`.

For headless machines:

```bash
~/.local/bin/bootstrap-op-connect-token --apply --headless
```

On subsequent logins `~/.zprofile` fetches the token from Keychain at runtime — the secret
never appears in any chezmoi-managed file.

### Notes

- On macOS, `~/.zprofile` contains a `security` command that reads the token from Keychain
  at shell login time. The token is in the OS environment only while you're logged in — it
  is never written to disk in any chezmoi file.
- The Connect server is only reachable via Tailscale. Tailscale must be running before
  `chezmoi init` or `chezmoi apply` on any machine.
- The `unset` subshell is required because `OP_CONNECT_TOKEN` is exported by the generated
  shell profile — without it, `op` switches to Connect mode and cannot reach the Private vault.
- **Work machines:** the age encryption key is not in the Automation vault. `fetch-age-key.sh`
  will warn and skip gracefully; encrypted source files will not be decryptable until the age
  identity is provisioned separately.
- **Token rotation:** update the token in the Private vault, then re-run the bootstrap script
  on each machine. On macOS the new token overwrites the Keychain entry; on Linux `--headless`
  exports the new token directly.
