# Setup

```
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password

All secrets are read via the 1Password CLI (`onepassword.mode = "account"`).

**Personal machines (macOS):** reads go through a read-only service account for the `Automation`
vault, so `chezmoi apply` and agents never prompt. Its token lives in the Keychain item
`op-service-account-automation`.

The first `chezmoi init --apply` bootstraps a bare Mac by itself: the `read-source-state.pre` hook
installs Homebrew and the 1Password CLI when missing, then asks once for the token and stores it in
the Keychain (input hidden, nothing in shell history or the process list). To set the item by hand
instead:

```bash
security add-generic-password -U -a "$USER" -s op-service-account-automation -w
```

Keep a backup of the token in `Private`; see
[Token backup and restore](docs/age-encryption.md#token-backup-and-restore).

Secrets chezmoi needs must live in `Automation`. For anything else (other vaults, writes) run
`OP_APP_AUTH=1 op …`. See [docs/age-encryption.md](docs/age-encryption.md#service-account-personal-machines).

**Work machines:** sign in before running `chezmoi apply`:

```bash
op signin
chezmoi init --apply nlopez
```

**Work machines:** the age encryption key is not stored in the work account's Automation vault.
`fetch-age-key.sh` will warn and skip gracefully; encrypted source files will not be
decryptable until the age identity is provisioned separately.
