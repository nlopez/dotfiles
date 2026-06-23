# Agent Guidelines — Dotfile Management with Chezmoi

## What this repo is

A [chezmoi](https://chezmoi.io/) dotfile management repository for synchronizing dotfiles, configurations, and scripts across multiple machines. **The goal of this repo is to maintain a fully declarative configuration that works identically on any machine.**

Chezmoi treats your home directory as immutable infrastructure version-controlled in Git — every file in `~` should be reproducible from the source tree alone. This means:

- **No manual edits, ever** — never edit files directly in `~`, and never run one-off commands to install, configure, or change anything on the system. Every change must go through the chezmoi source tree so it is reproducible on every machine.
- **No one-off commands** — don't run `brew install foo`, `pi install`, `npm install`, or any other imperative tool invocation as a standalone action. The correct workflow is always: declare the change in the source tree → `chezmoi apply`. The appropriate `.chezmoiscripts/` hook will execute the command as part of apply.
- **Idempotent & portable** — any machine can run `chezmoi apply` and end up with an identical, working configuration.
- **Declarative over imperative** — prefer static templates (`.tmpl`) with `.chezmoi.os`/`.chezmoi.arch` conditionals over shell scripts. Scripts belong in `.chezmoiscripts/` only for one-time setup that can't be expressed as config files.
- **Source of truth lives in Git** — the source tree under `home/` is the single source of truth. The destination (`~`) is ephemeral and always derived from it.

## Quick setup

```sh
op signin
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password

All chezmoi secrets are read via the 1Password CLI (`onepassword.mode = "account"`).
Sign in with `op signin` before running `chezmoi apply`. No Connect token or bootstrap
script is required.

> See [README.md](README.md#1password) for full details.

## Commands

```sh
chezmoi apply --dry-run          # Preview changes
chezmoi status                   # Diff source vs destination
chezmoi diff                     # Show what would change
chezmoi add ~/.config/foo/bar    # Add a new file
chezmoi edit ~/.config/foo/bar   # Edit via source tree
chezmoi source-path ~/.zshrc     # Resolve destination → source
```

## Directory structure

```
.
├── docs/                          # Agent documentation (split out of AGENTS.md)
│   ├── getting-started.md         # What this repo is + quick setup
│   ├── core-concepts.md           # Source state, repo layout, never edit ~
│   ├── dotfile-workflows.md       # Adding/removing dotfiles, re-apply guarantee
│   ├── age-encryption.md          # Post-quantum age encryption workflows
│   ├── tools-and-validation.md    # Linting, Pi plugins, validation
│   └── quick-reference.md         # Commands, repo navigation, path disambiguation
├── home/                          # Chezmoi source tree (see .chezmoiroot)
│   └── .chezmoiscripts/           # Post-apply and setup scripts
├── scripts/                       # Project scripts (linting, not chezmoi-managed)
└── .chezmoiroot                   # Value: home
```

## Script patterns

Chezmoi supports three script patterns — use the right one for your use case:

### `.chezmoiscripts/` — post-apply and setup scripts

Place scripts in `home/.chezmoiscripts/`. The top-level scripts (non-platform-specific) go directly in the directory; platform-specific ones go in `darwin/` or `linux/` subdirectories.

| Prefix                 | When it runs                                                 |
| ---------------------- | ------------------------------------------------------------ |
| `run_after_*`          | After all dotfiles have been updated (every `chezmoi apply`) |
| `run_onchange_after_*` | After all dotfiles updated, only if script content changed   |
| `run_once_after_*`     | Only the first time (tracked by SHA256)                      |

```sh
home/.chezmoiscripts/run_after_reload-tmux.sh       # Reloads tmux every apply
home/.chezmoiscripts/run_onchange_after_pnpm-globals.py.tmpl  # Platform-specific, only on change
home/.chezmoiscripts/run_once_after_install-iosevka-nf-fonts.sh.tmpl  # One-time install
```

- No executable bit needed — chezmoi handles this internally.
- Must include a `#!` shebang (chezmoi executes them via `exec(3)`).
- Must be idempotent.
- Tracked by git, **not** added via `chezmoi add` (source tree is protected).

### `.chezmoiscripts/` — one-time setup and package installation

Place non-config scripts in `.chezmoiscripts/` with prefixes like `run_once_`, `run_onchange_`, `run_before_`, `run_after_` for platform-specific one-off setup (package installs, font installs, etc.). See [Use scripts to perform actions](https://chezmoi.io/user-guide/use-scripts-to-perform-actions/).

### `run_` scripts — run on every apply

Files with the `run_` prefix in the source directory execute every `chezmoi apply` (interleaved with file updates). Use `run_before_` or `run_after_` attributes to control ordering. See the official docs for details.

> ⚠️ **Don't launch chezmoi from inside a `run_` or hook script** — a running `chezmoi apply` will fail if it tries to start another instance. If you need chezmoi-specific info, use templates instead.

## Full documentation

| File                                                         | Contents                                                       |
| ------------------------------------------------------------ | -------------------------------------------------------------- |
| [docs/getting-started.md](docs/getting-started.md)           | What this repo is, setup, quick commands                       |
| [docs/core-concepts.md](docs/core-concepts.md)               | Source state, `.chezmoiroot`, naming, templates, data, scripts |
| [docs/dotfile-workflows.md](docs/dotfile-workflows.md)       | Adding/removing dotfiles, re-apply guarantee, boundaries       |
| [docs/age-encryption.md](docs/age-encryption.md)             | Age post-quantum encryption, key setup, secrets workflows      |
| [docs/tools-and-validation.md](docs/tools-and-validation.md) | Linting, Pi plugin management, validation rules                |
| [docs/quick-reference.md](docs/quick-reference.md)           | Commands, repo navigation, path disambiguation                 |

## XDG Base Directory Compliance

All new tool configurations **must** follow the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/). The four env vars are exported in `dot_zprofile.tmpl`:

| Variable          | Default          | Purpose                     |
| ----------------- | ---------------- | --------------------------- |
| `XDG_CONFIG_HOME` | `~/.config`      | Config files                |
| `XDG_DATA_HOME`   | `~/.local/share` | Persistent data             |
| `XDG_STATE_HOME`  | `~/.local/state` | Logs, history, state        |
| `XDG_CACHE_HOME`  | `~/.cache`       | Non-essential / regenerable |

### Rule for new tool additions

1. Check if the tool reads `$XDG_CONFIG_HOME` natively → place source under `dot_config/<tool>/`.
2. If the tool requires an env var to redirect its config (e.g. `TF_CLI_CONFIG_FILE`) → add the export to `env.tmpl` and place the source under the XDG path.
3. If the tool has **no** XDG support → place it at the unavoidable location, add it to the **Intentionally non-XDG** table below, and do **not** add a `.chezmoiremove` entry for the XDG path.
4. When relocating an existing tool, always add the old `~/.<name>` path to `.chezmoiremove` (with an OS guard when macOS-only) so machines that are already configured are cleaned up.

### Migrated to XDG

| Tool                   | Config / data location                  | How                                               |
| ---------------------- | --------------------------------------- | ------------------------------------------------- |
| Terraform CLI          | `~/.config/terraform/terraformrc`       | `TF_CLI_CONFIG_FILE` env var                      |
| Homebrew Brewfile      | `~/.config/brew/Brewfile`               | `HOMEBREW_BUNDLE_FILE` env var                    |
| Oh My Zsh              | `~/.local/share/oh-my-zsh`              | `export ZSH=` in `.zshrc`                         |
| atuin config           | `~/.config/atuin/`                      | Native XDG support                                |
| atuin data             | `~/.local/share/atuin/`                 | `db_path`/`key_path`/`session_path` in config     |
| atuin logs             | `~/.local/state/atuin/logs`             | `[logs] dir =` in config                          |
| bat                    | `~/.config/bat/`                        | Native XDG support                                |
| ghostty                | `~/.config/ghostty/`                    | Native XDG support                                |
| git                    | `~/.config/git/`                        | Native XDG support                                |
| jj                     | `~/.config/jj/`                         | Native XDG support                                |
| k9s                    | `~/.config/k9s/`                        | Native XDG support                                |
| neovim                 | `~/.config/nvim/`                       | Native XDG support                                |
| pnpm data              | `~/.local/share/pnpm/`                  | `PNPM_HOME` env var                               |
| Go data                | `~/.local/share/go/`                    | `GOPATH` env var                                  |
| rclone                 | `~/.config/rclone/`                     | Native XDG support                                |
| terraform plugin cache | `~/.cache/terraform/`                   | `plugin_cache_dir` in config                      |
| tmux                   | `~/.config/tmux/`                       | Native XDG support                                |
| zabrze                 | `~/.config/zabrze/`                     | Native XDG support                                |
| Zed                    | `~/.config/zed/`                        | Native XDG support                                |
| zsh startup files      | `~/.config/zsh/{zshenv,zprofile,zshrc}` | `ZDOTDIR` in bootstrap `~/.zshenv`                |
| Pi agent               | `~/.config/pi/agent/`                   | `PI_CODING_AGENT_DIR` env var                     |
| Context-mode           | `~/.local/state/pi/context-mode/`       | `CONTEXT_MODE_DIR` env var                        |
| MCP shared config      | `~/.config/mcp/mcp.json`                | Native XDG support (pi-mcp-adapter best practice) |

### Intentionally non-XDG

These tools have no XDG support and no env-var workaround. Do not attempt to move them.

| Tool            | Location                        | Reason                                                                                                     |
| --------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SSH             | `~/.ssh/`                       | OpenSSH does not support XDG                                                                               |
| bash/sh startup | `~/.profile`, `~/.bash_profile` | POSIX startup files; `.bash_profile` delegates to `.profile`; actual config in `~/.config/shell/env` (XDG) |
| omlx root       | `~/.omlx/`                      | Root dir hardcoded; only `model_dirs` is redirected to `~/.local/share/omlx/models`                        |
| Terraform data  | `~/.terraform.d/`               | `TF_DATA_DIR` is per-workspace only; not safe to set globally                                              |

## ⚠️ Boundaries

### ✅ Always do

- **Declare first, then apply** — every change (package, config, tool, plugin) must be declared in the source tree before anything touches `~`. Run `chezmoi apply` to materialize it; the relevant `.chezmoiscripts/` hook will execute any required commands automatically.
- Edit via `chezmoi source-path <path>` or `chezmoi edit <path>`
- Verify with `chezmoi apply --dry-run` before committing
- Use templates for conditional logic (`.chezmoi.os`, `.chezmoi.arch`, etc.)
- Keep scripts idempotent — they must succeed even if already run
- For chezmoi `modify_` files, follow target-type semantics: plain `modify_*` files are
  scripts; only use `chezmoi:modify-template` when rendered template output should become
  the final file contents; modify templates must not have a `.tmpl` suffix
- Add Pi plugins by declaring them in `.chezmoidata/pi.yaml` → `pi.packages`, then running `chezmoi apply` (the `run_onchange_after_pi-packages.py.tmpl` script reconciles the install automatically)

### ⚠️ Ask first

- Change the `.chezmoiroot` file
- Modify the `.chezmoiignore` rules
- Change age encryption recipients or keys
- Remove a configuration deployed to multiple machines
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do

- **Make one-off changes** — never run an imperative command (e.g., `brew install`, `pi install`, `npm install`, `echo '…' >> ~/.zshrc`) as a standalone action. If a change is worth making, it belongs in the source tree.
- Edit files directly in `~` — they will be overwritten on next `chezmoi apply`
- Append to live config files (e.g., `echo 'foo' >> ~/.zshrc`)
- Run `pi install` directly to add plugins — declare them in `.chezmoidata/pi.yaml` and let `chezmoi apply` handle installation
- Commit secrets or credentials to the repo
- Bypass pre-commit hooks

## Platform-Specific Notes

### Aurora Linux (Universal Blue — Fedora Kinoite-based)

Aurora is an immutable, image-based distro with a **three-tier package management** strategy:

1. **rpm-ostree** — Immutable base system. Layering packages (`rpm-ostree layer`) is **strongly discouraged** (last resort only) due to dependency breakage risks and slower updates.
2. **Flatpak** — Primary method for GUI applications (via the Bazaar app from Flathub).
3. **Homebrew (Linuxbrew)** — Command-line tools installed at `/home/linuxbrew/.linuxbrew`. Configure via `packages.yaml` → `linux.brews` section.
4. **Distrobox** — Fallback for CLI tools not available via Flatpak or Homebrew. Creates containers with other distros' package managers (dnf, apt, etc.).
5. **blue-build** — Build your own image template for adding multiple layered packages (advanced).

**Key Aurora-specific rules:**

- **Never** edit files directly in `/` (the root filesystem is read-only on the immutable base).
- Use `rpm-ostree update` to pull base OS updates (atomic reboot required).
- Prefer Homebrew CLI tools over `rpm-ostree layer` whenever possible.
- For Neovim: install via Homebrew (`brew install neovim`), NOT via `rpm-ostree layer`.
- The `/home/linuxbrew/.linuxbrew` prefix must be in `$PATH` — this is handled by the Linux brew prefix config.

### macOS

- Neovim installed via Homebrew (`brew install neovim`).
- CLI tools configured via `packages.yaml` → `darwin.brews` section.
- GUI apps via Homebrew Casks (or mas for Mac App Store apps).

### Neovim Direct Management

The Neovim configuration is **directly managed** in the chezmoi source tree — not via external git-repo:

```
home/dot_config/nvim/
├── init.lua              # Bootstrap entry (sources config/lazy.lua)
├── README.md             # Usage documentation
├── stylua.toml           # Lua formatting config
├── lua/
│   ├── config/           # LazyVim config files
│   │   ├── lazy.lua      # lazy.nvim bootstrap + LazyVim import
│   │   ├── options.lua   # Neovim options
│   │   ├── keymaps.lua   # Neovim keybindings
│   │   ├── autocmds.lua  # Neovim autocommands
│   │   └── overrides.lua # LazyVim opts overrides
│   ├── mapping/          # Custom keybinding extensions
│   │   └── custom.lua
│   └── plugins/          # Custom plugin specs
│       └── init.lua
└── package.json          # Package metadata
```

- **Binary**: macOS and Aurora Linux use Homebrew (via `packages.yaml` → `brews.base`).
- **Config**: Directly in `home/dot_config/nvim/` — full `chezmoi diff`/`status` visibility.
- **Extensions**: Edit `lua/plugins/init.lua` for plugin specs, `lua/config/overrides.lua` for LazyVim opts.

## Further Reading

- [chezmoi Documentation](https://chezmoi.io/docs/)
- [Source Format](https://chezmoi.io/reference/source-formats/verbatim/)
- [External Sources](https://chezmoi.io/reference/external-sources/)
- [Using External Data](https://chezmoi.io/reference/data/)
- [State Management](https://chezmoi.io/docs/concepts/state/)
- [Recipes](https://chezmoi.io/recipes/) — community-contributed patterns
- [Aurora Linux Package Management](https://docs.getaurora.dev/guides/software/) — Flatpak, rpm-ostree, Distrobox
- [Aurora Linux Architecture](https://deepwiki.com/ublue-os/aurora) — Three-tier package management
