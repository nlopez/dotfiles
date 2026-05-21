# Agent Guidelines — Dotfile Management with Chezmoi

## What this repo is

A [chezmoi](https://chezmoi.io/) dotfile management repository for synchronizing dotfiles, configurations, and scripts across multiple machines. Chezmoi treats your home directory as immutable infrastructure version-controlled in Git.

## Setup

```sh
# Install chezmoi
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init <owner>/<repo>

# Apply dotfiles to current machine
chezmoi apply
```

See the [chezmoi docs](https://chezmoi.io/docs/) for installation and getting started.

## Core Concepts & Best Practices

### Source state → destination state

Chezmoi manages a mapping from files in the repo (source state) to files in the home directory (destination state). Understanding the two states is fundamental to working with chezmoi:

- **Source state** — files and metadata as stored in the repo.
- **Destination state** — files as they appear in `~` (or any other target path).

Key commands for inspection:

```sh
chezmoi source-path       # Show the source file for a given destination path
chezmoi status            # Diff source vs. destination state
chezmoi diff              # Show what would change on apply
chezmoi apply             # Reconcile destination with source
chezmoi data              # Inspect the rendered data map
```

### Repository layout & `.chezmoiroot`

This repo is **not** a flat chezmoi source tree. A `.chezmoiroot` file (value: `home`) sets an alternative source root, meaning the chezmoi source tree lives under `home/` — the repo root contains non-chezmoi files alongside it.

```sh
cat .chezmoiroot
# Output: home
```

**Repo root** (NOT part of the chezmoi source tree):

| Path | Purpose |
|------|--------|
| `AGENTS.md` | Agent documentation for this repo |
| `.chezmoiroot` | Specifies `home` as the chezmoi source root (tracked by git) |
| `CLAUDE.md` | Claude code assistant documentation |
| `README.md` | Repository readme |
| `renovate.json` | Renovate dependency update config |
| `scripts/` | Project scripts (linting, helper tools) — **not** chezmoi-managed |
| `pyproject.toml` | Python project config (uv/pip) |
| `uv.lock` | uv dependency lock file |

**Under `home/`** (the chezmoi source tree):

| Pattern | Destination | Notes |
|---------|-------------|-------|
| `home/dot_<name>` | `~/.<name>` | Dotfiles |
| `home/dot_dirname/` | `~/.dirname/` | Directory source |
| `home/config/<path>` | `~/.config/<path>` | XDG-style config |
| `home/bin/<name>` | `~/.local/bin/<name>` | Executables (via bin/ prefix) |

**Under `home/`** — chezmoi special directories:

| Source path | Purpose |
|-------------|--------|
| `home/.chezmoiscripts/` | Install/init scripts (run after dotfiles are applied) |
| `home/.chezmoidata/` | Data files for templates (YAML) |
| `home/.chezmoiignore.tmpl` | Ignored paths (`.chezmoiignore` is at the **repo root**, not under the root override) |

**This is critical:** when `.chezmoiroot` is `home`, all chezmoi special directories live **under `home/`**, not at the repo root. Specifically:

- `.chezmoiscripts/` → `home/.chezmoiscripts/` (scripts run as part of `chezmoi apply`)
- `.chezmoidata/` → `home/.chezmoidata/`
- All dotfile/config/bin sources live under `home/`
- **`.chezmoiignore`** is at the **repo root** (not under the root override)

**When modifying scripts, always check `.chezmoiroot` first** — the script directory is at `home/.chezmoiscripts/`, not `.chezmoiscripts/` at the repo root.

**When locating files, use `chezmoi source-path`** — this resolves a destination path to its source file regardless of the `.chezmoiroot` override:

```sh
chezmoi source-path ~/.config/tmux/tmux.conf
# Output: home/dot_config/tmux/tmux.conf
```

### ⚠️ Never edit files in `~` directly — always go through chezmoi

**This is the single most important rule in this repo.** Every file that exists in `~` (or any destination path) is managed by chezmoi. **Never edit a file directly in `~`** — it will be overwritten the next time `chezmoi apply` runs.

**Rule: Always edit the source tree.** Use one of these workflows:

1. **`chezmoi source-path <path>`** → Find the source file, edit it directly
2. **`chezmoi edit <path>`** → Open the source file in `$EDITOR` (auto-resolves the source)
3. **`chezmoi apply`** → Reconciles `~` with the source tree

**Do NOT:**
- `vim ~/.config/tmux/tmux.conf` — edit the live file directly
- `echo 'foo' >> ~/.zshrc` — append to the live file
- `pi install <package>` — writes directly to `~/.pi/agent/settings.json` (lost on next `chezmoi apply`)
- Create files under `~/.config/`, `~/.local/`, `~/` that aren't in the source tree

**Always:**
- Edit `home/dot_config/tmux/tmux.conf` (the chezmoi source)
- Edit `home/dot_zshrc.tmpl` (the chezmoi source template)
- Edit `home/dot_pi/agent/modify_settings.json.tmpl` (the Pi settings template)
- Run `chezmoi apply` to push changes to `~`

The only exception is files completely outside this repo's purview (e.g., `/tmp/`, unrelated projects). But if a file lives in `~` and this repo manages it, **always edit through chezmoi**.

#### How this works in practice

When you edit a chezmoi-managed file:

```sh
# WRONG: editing the live file (will be overwritten)
vim ~/.zshrc
echo 'alias foo=bar' >> ~/.zshrc  # LOST on next chezmoi apply

# RIGHT: editing the source tree (persists across apply)
chezmoi edit ~/.zshrc              # opens home/dot_zshrc.tmpl
edit home/dot_zshrc.tmpl          # same thing, just more explicit
chezmoi apply                     # renders template → ~/.zshrc
```

When `~/.zshrc` or `~/.pi/agent/settings.json` or `~/.config/...` are shown as modified in `chezmoi status`, it means the source tree and live file are in sync — **don't touch the live file**. Any drift (source changed but `~` hasn't) is fixed by `chezmoi apply`.

### Idempotency and reproducibility

**Every chezmoi change must be idempotent and reproducible.** The source tree is the single source of truth — anyone (including you on a fresh install or a new machine) should be able to run:

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init <owner>/<repo>
chezmoi apply
```

and end up with an identical, working configuration. This means:

- **Never rely on side-effects from other tools.** If a package install script installs something, ensure it doesn't leave orphaned config files in `~` that won't be recreated on a fresh apply. Use `empty_` or `dir_` prefixes to handle files/dirs that should exist but aren't managed by templates.
- **Use templates for conditional logic.** Host-specific or OS-specific config should use `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.sourcePath`, and data files — not branch the repo or rely on manual post-install steps.
- **Use scripts for one-time setup.** Package managers, browser extensions, and init steps that can't be expressed as static files belong in `.chezmoiscripts/`. Keep them idempotent — they must succeed even if already run.

#### Removing configurations

When removing a dotfile or config, don't just delete it from the repo. You must also clean up:

1. **The source file** — remove the `dot_<name>`, `config/...`, or `bin/...` entry from the repo.
2. **Any leftover artifacts** — if the config created ancillary files (e.g., data dirs, symlinks, child configs), add a cleanup script in `.chezmoiscripts/` (e.g., `darwin/01_cleanup_old_config.sh`) that removes them.
3. **The `empty_`/`dir_` markers** — if you created `empty_` or `dir_` entries just to prevent chezmoi from recreating a path, remove those too once cleanup is done.

This ensures that re-applying chezmoi on a machine that previously had the old config ends up in a clean state rather than leaving stale artifacts.

#### Re-apply guarantee

**`chezmoi apply` must be a safe, complete reset.** Re-running it should:
- Recreate all managed files to match the source tree
- Not break any tools that depend on the config
- Leave no orphaned files from removed configs
- Produce the same result regardless of how many times it's run

Before committing any change, ask: "If I wiped my home directory and ran `chezmoi apply` from scratch, would everything work?" If the answer is no, the change needs cleanup scripts, empty/dir markers, or additional template guards.

### Source file naming convention

Files in the repo root are deployed based on naming:

| Source file name        | Destination              | Notes                                      |
|-------------------------|--------------------------|---------------------------------------------|
| `dot_<filename>`        | `~/.<filename>`          | Dotfiles                                     |
| `dot_dirname/`          | `~/.dirname/`            | Directory (contents deployed inside)         |
| `config/dirname/file`   | `~/.config/dirname/file` | XDG-style config                             |
| `bin/script`            | `~/.local/bin/script`    | Executable (marked executable)               |

Use prefixes like `empty_`, `secure_`, `exact_`, `sym_`, `dir_` to control behavior ([source format docs](https://chezmoi.io/reference/source-formats/verbatim/)).

### Templates

Files ending in `.tmpl` are processed as [Go templates](https://pkg.go.dev/text/template). Chezmoi provides built-in variables like `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.environ`, and `.chezmoi.sourcePath` for conditional logic:

```gotemplate
{{- if eq .chezmoi.os "darwin" -}}
# macOS-specific config
{{- else if eq .chezmoi.os "linux" -}}
# Linux-specific config
{{- end -}}
```

Templates are rendered with `chezmoi execute-template` during `apply`. Use `.chezmoi.toml.tmpl` for global template configuration.

### Data files

Structured configuration data lives in `.chezmoidata/` (YAML by default). Data is merged across files and made available as a map in templates:

```gotemplate
{{ .mydata.key }}
```

This is the recommended place to externalize values that vary by OS, host, or user — keeping templates clean and data declarative. Per-platform overrides follow the pattern `.chezmoidata/{darwin,linux,windows}/`. See [external data docs](https://chezmoi.io/reference/data/).

### Scripts

`.chezmoiscripts/` contains installation/initialization scripts that run after dotfiles are applied. Organize by OS:

```
.chezmoiscripts/
  darwin/   # scripts for macOS
  linux/    # scripts for Linux
  windows/  # scripts for Windows
```

Scripts run in order by name. Use them for package managers, browser extensions, or one-time setup steps that dotfiles alone cannot handle. See [scripts docs](https://chezmoi.io/docs/reference/scripts/).

### External dependencies

Third-party resources (plugins, themes, etc.) are managed via `.chezmoiexternal.toml`, which supports Git repositories and tarball URLs. Chezmoi fetches and extracts these into the source tree during `init`/`apply`. See [external sources docs](https://chezmoi.io/reference/external-sources/).

### Pi plugins — install via pnpm, not `pi install`

> ⚠️ **Pi does not self-update its own plugins.** The `pi install <package>` command writes directly to `~/.config/pi/settings.json` (the live destination file) and is **not** tracked by chezmoi. Packages installed this way will be lost on the next `chezmoi apply` and won't be reproduced on a fresh machine.

**Always add Pi plugins (extensions, skills, adapters) through pnpm** so they are version-controlled and automatically installed on every machine:

1. Add the package name to the `pnpm.personal` (or `pnpm.base`) list in
   `home/.chezmoidata/darwin/packages.yaml` (and the equivalent `linux/` file if needed).
2. Run `chezmoi apply` — the `run_onchange_after_pnpm-globals.sh.tmpl` script picks up the change and installs it globally via `pnpm add -g`.
3. Commit the data file change.

The MCP adapter for Pi (`pi-mcp-adapter`) follows the same rule and is declared in `packages.yaml` under `pnpm.personal`.

## Linting / Validation

Project linting is automated via pre-commit hooks and custom scripts. Ensure all changes pass validation before committing:

```sh
# Lint all JSON templates (renders for darwin/linux/windows)
uv run scripts/jsonlint.py

# Shellcheck all .sh and .sh.tmpl files in .chezmoiscripts/
uv run scripts/shellcheck.py

# Run all pre-commit hooks (gitleaks, yamlfmt, jsonlint, shellcheck)
pre-commit run --all-files
```

## Navigating the repo (quick reference)

When working in this repo, keep these mental models in mind:

**The repo root is NOT the chezmoi source root.**
- Files at the repo root (`AGENTS.md`, `scripts/`, `pyproject.toml`) are plain Git files.
- The chezmoi source tree is under `home/` (the value in `.chezmoiroot`).
- Use `ls .local/share/chezmoi/home/` or `chezmoi source-path` to find sources.

**`home/` is the chezmoi source root.**
- All dotfile/config/bin sources live under `home/`.
- Chezmoi special dirs (`.chezmoiscripts/`, `.chezmoidata/`) are under `home/`.
- `chezmoi source-path` resolves destination → source under `home/`.

**Important path disambiguation:**

| What you want | Where it lives |
|---------------|---------------|
| This file (`AGENTS.md`) | Repo root: `AGENTS.md` |
| chezmoi scripts | `home/.chezmoiscripts/` (NOT repo root `scripts/`) |
| Lint scripts | Repo root: `scripts/` (NOT chezmoi-managed) |
| The `.chezmoiroot` file | Repo root: `.chezmoiroot` |
| Source for `~/.gitconfig` | `home/dot_gitconfig` |
| Source for `~/.config/tmux/` | `home/dot_config/tmux/` |

## Adding a new dotfile

1. Create the file in the repo using the naming convention (`dot_<name>`, `config/...`, `bin/...`).
2. If it needs templating or data-driven values, use a `.tmpl` extension and reference data from `.chezmoidata/`.
3. Add it to `.chezmoiignore` only if it should exist in source but not be deployed to certain platforms.
4. Run `chezmoi apply --dry-run` to verify, then commit.

## Useful Chezmoi Commands

| Command                         | Purpose                                          |
|---------------------------------|--------------------------------------------------|
| `chezmoi apply`                 | Apply all dotfiles to current machine             |
| `chezmoi apply --dry-run`       | Preview changes without applying                  |
| `chezmoi status`                | Show source vs. destination differences           |
| `chezmoi add <path>`            | Add a file/dir to source state                    |
| `chezmoi edit <path>`           | Edit a source file (creates it if missing)        |
| `chezmoi forget <path>`         | Remove a file from source state                   |
| `chezmoi source-path <path>`    | Resolve a destination path to its source file     |
| `chezmoi data`                  | Print the merged data map for template debugging  |
| `chezmoi cat <path>`            | Show rendered output of a source file             |

## age Post-Quantum Encryption

This repo uses [age](https://age-encryption.org/) with hybrid ML-KEM-768 + X25519 post-quantum keys to encrypt machine-class-specific secrets. Work and personal machines each have their own keypair; each private key lives exclusively in its respective 1Password account and is never committed to the repo.

### How it works

- **Work secrets** → `~/.config/work-secrets/` — encrypted to the work age recipient, deployed only on work machines.
- **Personal secrets** → `~/.config/personal-secrets/` — encrypted to the personal age recipient, deployed only on personal machines.
- **Same-path / different-value secrets** (e.g. `~/.env` with machine-specific tokens) → use `.tmpl` files with `onepasswordRead` instead of age encryption.
- The age private key (identity) is fetched from 1Password automatically via `hooks.read-source-state.pre` and written to `~/.local/share/chezmoi-age/identity.txt` before any decryption happens.

### Initial setup on a new machine (one-time)

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

### Day-to-day operations

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

### Same-path / different-value secrets

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

### Key rotation

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

### Source tree layout

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

### Files that are never in the repo

| Path | What it is |
|------|------------|
| `~/.local/share/chezmoi-age/identity.txt` | age private key — written by hook, never committed |
| 1Password item `Private/age-key/private-key` | Source of truth for the private key |

## Further Reading

- [chezmoi Documentation](https://chezmoi.io/docs/)
- [Source Format](https://chezmoi.io/reference/source-formats/verbatim/)
- [External Sources](https://chezmoi.io/reference/external-sources/)
- [Using External Data](https://chezmoi.io/reference/data/)
- [State Management](https://chezmoi.io/docs/concepts/state/)
- [Recipes](https://chezmoi.io/recipes/) — community-contributed patterns
