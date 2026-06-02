# Setup

```
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password

All secrets are read via the 1Password CLI (`onepassword.mode = "account"`). Sign in before
running `chezmoi apply`:

```bash
op signin
chezmoi init --apply nlopez
```

**Work machines:** the age encryption key is not stored in the work account's Automation vault.
`fetch-age-key.sh` will warn and skip gracefully; encrypted source files will not be
decryptable until the age identity is provisioned separately.
