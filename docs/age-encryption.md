# Age Post-Quantum Encryption

This repo uses [age](https://age-encryption.org/) with hybrid ML-KEM-768 + X25519 post-quantum keys to encrypt machine-class-specific secrets. Work and personal machines each have their own keypair; each private key lives exclusively in its respective 1Password account and is never committed to the repo.

## How it works

- **Work secrets** → `~/.config/work-secrets/` — encrypted to the work age recipient, deployed only on work machines.
- **Personal secrets** → `~/.config/personal-secrets/` — encrypted to the personal age recipient, deployed only on personal machines.
- **Same-path / different-value secrets** (e.g. `~/.env` with machine-specific tokens) → use `.tmpl` files with `onepasswordRead` instead of age encryption.
- The age private key (identity) is fetched from 1Password automatically via `hooks.read-source-state.pre` and written to `~/.local/share/chezmoi-age/identity.txt` before any decryption happens.

## Initial setup on a new machine (one-time)

Before working with age-encrypted secrets, bootstrap the 1Password Connect token:

```sh
# macOS
scripts/bootstrap-op-connect-token --apply
# Headless
scripts/bootstrap-op-connect-token --apply --headless
```

This sets up `OP_CONNECT_TOKEN` so `chezmoi` can read secrets from 1Password Connect.
See [README.md](../README.md#1password-connect) for details.

```sh
# 1. Generate a post-quantum keypair (do this once per machine class, not per machine).
age-keygen -pq -o /tmp/age-key.txt          # prints age1pq1... public key to stderr
age-keygen -y /tmp/age-key.txt              # re-extract public key to stdout

# 2. Store the private key in 1Password:
#   Work   → Account: datadog.1password.com | Vault: Private | Item: age-key | Field: private-key
#   Personal → Account: my.1password.com   | Vault: Private | Item: age-key | Field: private-key

# 3. Paste the age1pq1... public key into the appropriate recipient file:
#   Work:     home/dot_local/share/chezmoi-age/work-recipient.txt
#   Personal: home/dot_local/share/chezmoi-age/personal-recipient.txt
#   (Replace the age1pq1REPLACE_WITH_... placeholder line.)

# 4. Commit the updated recipient file.
rm /tmp/age-key.txt
```

On subsequent machines of the same class, no key generation is needed — `chezmoi apply` fetches the key from 1Password automatically.

## Day-to-day operations

```sh
# Add a new encrypted work secret (file must already be at destination path):
chezmoi add --encrypt ~/.config/work-secrets/my.env
# chezmoi moves the source file into home/dot_config/private_work-secrets/
# and encrypts it with the work recipient key.

# Edit an existing encrypted secret transparently:
chezmoi edit ~/.config/work-secrets/my.env
# chezmoi decrypts to a temp file, opens $EDITOR, re-encrypts on save.

# Inspect what a ciphertext is encrypted to (verify PQ):
age-inspect "$(chezmoi source-path ~/.config/work-secrets/my.env)"
# Should show: recipient type "mlkem768x25519" / "This file uses post-quantum encryption."

# Verify the full apply/decrypt cycle:
chezmoi apply --dry-run
chezmoi diff
```

## Same-path / different-value secrets

For secrets that must exist at the same destination path on both machine classes but with different values, use a `private_` prefixed `.tmpl` source file that calls `onepasswordRead`:

```
# Source: home/dot_config/sometool/private_dot_env.tmpl
{{ if .work -}}
API_KEY={{ onepasswordRead "op://Private/sometool-work/api-key" "datadog.1password.com" }}
{{ else if .personal -}}
API_KEY={{ onepasswordRead "op://Private/sometool-personal/api-key" "my.1password.com" }}
{{ end -}}
```

Verify with: `chezmoi cat ~/.config/sometool/.env`

## Key rotation

```sh
# 1. Generate a new keypair and store in 1Password (same procedure as initial setup).
# 2. Update the recipient file in the source tree with the new age1pq1... public key.
# 3. Re-encrypt every affected file:
for dest in ~/.config/work-secrets/*; do
  chezmoi add --encrypt "${dest}"
done
# 4. Delete the old identity file so the hook fetches the new one:
rm ~/.local/share/chezmoi-age/identity.txt
# 5. Run chezmoi apply --dry-run to confirm everything decrypts cleanly.
# 6. Commit and push.
```

## Source tree layout

```
home/
  dot_local/share/chezmoi-age/
    work-recipient.txt        # age1pq1... public key for work  (NOT secret, committed)
    personal-recipient.txt    # age1pq1... public key for personal (NOT secret, committed)
  dot_config/
    private_work-secrets/     # → ~/.config/work-secrets/ (mode 700, work machines only)
      encrypted_*             # age-encrypted files
    private_personal-secrets/ # → ~/.config/personal-secrets/ (mode 700, personal machines only)
      encrypted_*             # age-encrypted files
scripts/
  fetch-age-key.sh            # hook: fetches identity from 1Password → ~/.local/share/chezmoi-age/identity.txt
```

## Files that are never in the repo

| Path                                         | What it is                                         |
| -------------------------------------------- | -------------------------------------------------- |
| `~/.local/share/chezmoi-age/identity.txt`    | age private key — written by hook, never committed |
| 1Password item `Private/age-key/private-key` | Source of truth for the private key                |

## ⚠️ Boundaries

### ✅ Always do

- Edit encrypted files via `chezmoi edit` (chezmoi handles decrypt/re-encrypt)
- Store age private keys in 1Password
- Use `age-inspect` to verify encryption recipients

### ⚠️ Ask first

- Add a new machine class (e.g., "staging")
- Change the encryption algorithm
- Revoke and regenerate machine keys

### 🚫 Never do

- Commit age identity files or private keys
- Hardcode secrets in templates (use `onepasswordRead` or age encryption)
- Share private keys across machine classes
