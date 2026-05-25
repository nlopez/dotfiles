# Core Concepts & Best Practices

## Source state → destination state

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

## Repository layout & `.chezmoiroot`

This repo is **not** a flat chezmoi source tree. A `.chezmoiroot` file (value: `home`) sets an alternative source root, meaning the chezmoi source tree lives under `home/` — the repo root contains non-chezmoi files alongside it.

```sh
cat .chezmoiroot
# Output: home
```

### Repo root (NOT part of the chezmoi source tree)

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

### Under `home/` (the chezmoi source tree)

| Pattern | Destination | Notes |
|---------|-------------|-------|
| `home/dot_<name>` | `~/.<name>` | Dotfiles |
| `home/dot_dirname/` | `~/.dirname/` | Directory source |
| `home/config/<path>` | `~/.config/<path>` | XDG-style config |
| `home/bin/<name>` | `~/.local/bin/<name>` | Executables (via bin/ prefix) |

### Chezmoi special directories (under `home/`)

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

## ⚠️ Never edit files in `~` directly — always go through chezmoi

**This is the single most important rule in this repo.** Every file that exists in `~` (or any destination path) is managed by chezmoi. **Never edit a file directly in `~`** — it will be overwritten the next time `chezmoi apply` runs.

### Rule: Always edit the source tree

Use one of these workflows:

1. **`chezmoi source-path <path>`** → Find the source file, edit it directly
2. **`chezmoi edit <path>`** → Open the source file in `$EDITOR` (auto-resolves the source)
3. **`chezmoi apply`** → Reconciles `~` with the source tree

### Wrong ✅ Correct

```sh
# WRONG: editing the live file (will be overwritten)
vim ~/.config/tmux/tmux.conf
echo 'alias foo=bar' >> ~/.zshrc                    # LOST on next chezmoi apply
pi install <package>                                # Writes to ~, lost on apply
```

```sh
# RIGHT: editing the source tree (persists across apply)
chezmoi edit ~/.zshrc          # opens home/dot_zshrc.tmpl
edit home/dot_zshrc.tmpl       # same thing, just more explicit
chezmoi apply                  # renders template → ~/.zshrc
```

The only exception is files completely outside this repo's purview (e.g., `/tmp/`, unrelated projects). But if a file lives in `~` and this repo manages it, **always edit through chezmoi**.

## Idempotency and reproducibility

**Every chezmoi change must be idempotent and reproducible.** The source tree is the single source of truth — anyone (including you on a fresh install or a new machine) should be able to run:

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init <owner>/<repo>
chezmoi apply
```

and end up with an identical, working configuration.

### Best practices

- **Never rely on side-effects from other tools.** If a package install script installs something, ensure it doesn't leave orphaned config files in `~` that won't be recreated on a fresh apply. Use `empty_` or `dir_` prefixes to handle files/dirs that should exist but aren't managed by templates.
- **Use templates for conditional logic.** Host-specific or OS-specific config should use `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.sourcePath`, and data files — not branch the repo or rely on manual post-install steps.
- **Use scripts for one-time setup.** Package managers, browser extensions, and init steps that can't be expressed as static files belong in `.chezmoiscripts/`. Keep them idempotent — they must succeed even if already run.

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

`.chezmoiscripts/` contains installation/initialization scripts that run after dotfiles are applied. Scripts run in order by name. Use them for package managers, browser extensions, or one-time setup steps that dotfiles alone cannot handle. See [scripts docs](https://chezmoi.io/docs/reference/scripts/).

#### OS subdirectory convention

A common pattern is to organize scripts under OS-specific subdirectories:

```
.chezmoiscripts/
  darwin/   # scripts for macOS
  linux/    # scripts for Linux
  windows/  # scripts for Windows
```

This is a **convention**, not a requirement. Chezmoi does not require OS-specific directories. You can also:

- **Place a script directly under `.chezmoiscripts/`** — it runs on all platforms. Use `.chezmoi.os` conditionals inside a `.tmpl` script to handle platform differences:

```gotemplate
#!/bin/bash
{{- if eq .chezmoi.os "darwin" }}
FONT_DIR="{{ .chezmoi.homeDir }}/Library/Fonts"
{{- else if eq .chezmoi.os "linux" }}
FONT_DIR="{{ .chezmoi.homeDir }}/.local/share/fonts"
{{- end }}
```

- **Use OS-specific directories** when scripts are entirely platform-specific with no shared logic, keeping them simpler and easier to read.

**Rule of thumb:** if the script has platform-specific logic *and* shared logic, use one script with `.chezmoi.os` conditionals. If the scripts are completely different per platform, use OS-specific directories to avoid template complexity.

In this repo, we use OS-specific directories for scripts that are entirely platform-specific (e.g., macOS-only Brewfile updates, Linux-only font cache rebuilds), and we consider placing shared scripts (like font merge scripts) directly under `.chezmoiscripts/` with conditionals when the logic overlaps substantially across platforms.

### External dependencies

Third-party resources (plugins, themes, etc.) are managed via `.chezmoiexternal.toml`, which supports Git repositories and tarball URLs. Chezmoi fetches and extracts these into the source tree during `init`/`apply`. See [external sources docs](https://chezmoi.io/reference/external-sources/).
