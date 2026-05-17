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

### chezmoi root override — `.chezmoiroot`

This repo uses a `.chezmoiroot` file to set an alternative source root. The file's contents specify which subdirectory is the chezmoi source root:

```sh
# Contents of .chezmoiroot
cat .chezmoiroot
home
```

**This is critical:** when `.chezmoiroot` is set (e.g. to `home`), all chezmoi special directories live **under that subdirectory**, not at the repo root. Specifically:

- `.chezmoiscripts/` → `home/.chezmoiscripts/` (scripts run as part of `chezmoi apply`)
- `.chezmoiignore` is at repo root (it is not subject to the root override)
- `.chezmoidata/` → `home/.chezmoidata/`
- All dotfile/config/bin sources live under `home/`

**When modifying scripts, always check `.chezmoiroot` first** — the script directory may not be at `.chezmoiscripts/` at the repo root but nested under the configured root instead.

### ⚠️ Do not edit live dotfiles directly

**Never make changes directly to files in `~` or any destination path.** All configuration changes must go through the chezmoi source tree in this repo. Editing a live dotfile will:

1. **Get overwritten on the next `chezmoi apply`** — your changes will be silently reverted to the source-of-truth.
2. **Not be version-controlled** — your edits will be lost forever on re-init or machine change.
3. **Create drift** — `chezmoi status` and `chezmoi diff` will no longer accurately reflect what you've customized.

The correct workflow:

1. Locate the **source** file using `chezmoi source-path <destination-path>` (e.g., `chezmoi source-path ~/.gitconfig`)
2. Edit the source file in the repo (or use `chezmoi edit <destination-path>`)
3. Validate with `chezmoi diff` and `chezmoi apply --dry-run`
4. Apply with `chezmoi apply` and commit your changes

If a file is managed by an external tool (e.g., Pi's `settings.json` updated at runtime by `pi install`), update the chezmoi managed version (`modify_settings.json.tmpl` or equivalent) rather than the live file directly.

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

## Further Reading

- [chezmoi Documentation](https://chezmoi.io/docs/)
- [Source Format](https://chezmoi.io/reference/source-formats/verbatim/)
- [External Sources](https://chezmoi.io/reference/external-sources/)
- [Using External Data](https://chezmoi.io/reference/data/)
- [State Management](https://chezmoi.io/docs/concepts/state/)
- [Recipes](https://chezmoi.io/recipes/) — community-contributed patterns
