## What this repo is

A [chezmoi](https://chezmoi.io/) dotfile management repository for managing personal dotfiles across macOS (darwin), Linux, and Windows. Applied via `chezmoi apply`.

## Setup

```
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## Linting / validation

All linting is done via Python scripts managed by `uv` (requires-python >=3.11, deps in `pyproject.toml`/`uv.lock`):

```
# Lint all JSON templates (renders for darwin/linux/windows)
uv run scripts/jsonlint.py

# Shellcheck all .sh and .sh.tmpl files in .chezmoiscripts/
uv run scripts/shellcheck.py

# Run all pre-commit hooks (gitleaks, yamlfmt, jsonlint, shellcheck)
pre-commit run --all-files
```

## Architecture

### Directory structure

```
home/                          # chezmoi "home" directory — files here map to ~
  .chezmoi.toml.tmpl           # Main config: OS detection (personal/work/headless), zsh plugin list
  .chezmoiexternal.toml.tmpl   # External deps: oh-my-zsh plugins, tmux plugins, HashiCorp skills
  .chezmoiignore.tmpl          # OS-specific ignore rules
  .chezmoidata/                # Per-OS override data
    darwin/packages.yaml       # Brew packages, mas apps for macOS
    linux/packages.yaml        # APT packages for Linux
    windows/packages.yaml      # Scoop packages for Windows
    aliases.yaml               # Shell abbreviations (zabrze + PowerShell)
    espanso.yaml               # Espanso expansions
  .chezmoiscripts/             # Per-OS installation scripts
    darwin/                    # brew bundle, filetypes, desktop config
    linux/                     # apt packages, brew, tailscale, chsh
    windows/                   # scoop, browser autoupdate
  .chezmoidata/                # Data files (see above)
  dot_config/                  # Files deployed to ~/.config/

.chezmoiscripts/               # Per-OS installation scripts (repo root — chezmoi only runs scripts here)
  darwin/                      # brew bundle, filetypes, desktop config
  linux/                       # apt packages, brew, tailscale, chsh
  windows/                     # scoop, browser autoupdate
    git/                       # Git config (multi-file: config, config_hobby, config_datadog, ignore, allowed_signers)
    zed/                       # Zed editor settings
    ghostty/                   # Ghostty terminal config
    tmux/                      # Tmux config
    atuin/                     # Atuin history
    k9s/                       # k9s CLI
    jj/                        #jj (josh) config
    zabrze/                    # zabrze aliases config
  dot_local/                   # Files deployed to ~/.local/
    bin/                       # Executables: brew, dolly, tfenv, tfplan, symlink_git
  dot_ssh/                     # SSH config
  dot_claude/                  # Claude-specific: hooks/bash-regex-permission.sh, skills/graphify
  dot_aerospace.toml           # → ~/.aerospace.toml (window manager)
  dot_Brewfile.tmpl            # → ~/Brewfile (Homebrew bundle)
  dot_p10k.zsh                 # → ~/.p10k.zsh (Powerlevel10k prompt)
  dot_terraformrc.tmpl         # → ~/.terraformrc
  dot_zprofile.tmpl            # → ~/.zprofile
  dot_zshrc.tmpl               # → ~/.zshrc (Oh My Zsh + Powerlevel10k + zsh plugins)
  empty_dot_hushlogin          # Empty file to create ~/.hushlogin
  exact_dot_oh-my-zsh/         # Deployed as ~/.oh-my-zsh (exact mode, not a dotfile)
  AppData/                     # Windows AppData (terraform.rc)
  Documents/                   # Windows Documents (PowerShell profiles)
  Library/                     # macOS Library
  scoop/                       # Windows scoop persist

scripts/                       # Python validation scripts (uv-managed)
  chezmoi_lib.py               # Shared library: chezmoi_root(), build_data(), render_template(), print_verbose()
  jsonlint.py                  # Renders .json/.json.tmpl for all 3 OSes and validates JSON
  shellcheck.py                # Renders .sh/.sh.tmpl in .chezmoiscripts/ and runs shellcheck
```

### Key patterns

- **Templates**: Files ending in `.tmpl` are Go templates rendered by `chezmoi execute-template`. They use `{{- if eq .chezmoi.os "darwin" -}}` style conditionals.
- **Data-driven config**: `.chezmoi.toml.tmpl` detects OS, hostname, personal vs work, headless mode. Per-OS packages live in `.chezmoidata/{darwin,linux,windows}/packages.yaml`.
- **External deps**: `.chezmoiexternal.toml.tmpl` pulls in oh-my-zsh plugins, tmux plugins, HashiCorp skills, etc. from GitHub archives.
- **Pre-commit hooks**: `.pre-commit-config.yaml` runs gitleaks, yamlfmt, jsonlint (via `scripts/jsonlint.py`), shellcheck (via `scripts/shellcheck.py`).
- **Renovate**: Auto-updates dependencies (external archives, HashiCorp skills) with automerge PRs. See `renovate.json`.

### Graphify

This project has a knowledge graph at `graphify-out/`. Before searching raw files for architecture questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure. After modifying code files, run `graphify update .` to keep the graph current (AST-only, no API cost).

**Team setup** (multi-device / multi-user):
- `graphify-out/manifest.json` and `graphify-out/cost.json` are gitignored (local metadata, not shared).
- `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md` are committed — all collaborators start with the same map.
- Run `graphify hook install` to enable the git merge driver that auto-unions graphs from parallel commits (no conflict markers).
- Run `graphify update .` when docs/research papers change (node-level refresh, no full regeneration).
