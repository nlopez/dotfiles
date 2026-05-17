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
