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
op signin   # work machines; personal machines need the Keychain token, see README.md#1password
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init --apply nlopez
```

## 1Password

All chezmoi secrets are read via the 1Password CLI (`onepassword.mode = "account"`).

- **Personal machines (macOS):** reads use a read-only service account for the `Automation`
  vault, with its token in the Keychain item `op-service-account-automation`. No prompts, for
  `chezmoi apply` or for agents. `~/.local/bin/shims/op` supplies the token to any `op` on
  `PATH`; `OP_APP_AUTH=1 op …` opts back into app auth (other vaults, writes).
- **In templates on personal machines,** read secrets with
  `output (joinPath .chezmoi.homeDir ".local/bin/op-automation") "read" "--no-newline" "op://Automation/…"`,
  not `onepasswordRead`, which runs `op signin` and prompts. Put new secrets in `Automation`.
- **Reference items by UUID, never by name.** Secret references use the vault ID and item ID,
  `op://<vault-id>/<item-id>/<field>` (the `Automation` vault is `evjh25ux2mnoufaut6qhvm2pdi`),
  so renaming an item or vault doesn't break them. Get the ID with
  `op item get "<title>" --vault Automation --format json | jq -r .id`. This applies to every
  `op://` reference: `op read`, `op inject` templates, varlock `op()`, `onepasswordRead`.
  Field names (`credential`, `url`, …) stay as-is.
- **Work machines:** sign in with `op signin` before running `chezmoi apply`.

No Connect token or bootstrap script is required.

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

### `chezmoi-fast` vs plain `chezmoi`

`chezmoi-fast` (`alias chezmoi-fast="CHEZMOI_SKIP_SECRETS=1 chezmoi"`, defined in
`dot_zshrc.tmpl`) skips 1Password reads and the templates/files built entirely from
secrets (see `.chezmoiignore`). **Default to `chezmoi-fast apply` / `chezmoi-fast
diff`** for ordinary edits (dotfiles, niri/ghostty/tool configs, scripts, etc.) — it's
faster and doesn't require `op signin`. **Use plain `chezmoi`** only when the change
actually touches secrets or age-encrypted files, or reads/writes something gated by
`onepassword.mode`/`CHEZMOI_SKIP_SECRETS` in `.chezmoiignore` or `dot_zprofile.tmpl` —
there, the secret-backed content must actually be materialized to verify the change.

## Git workflow

- **Make and test all changes in a worktree:** Create a worktree (`wt switch --create <branch>`) before editing, and test your changes there (for example with `chezmoi-fast apply --dry-run` / `chezmoi apply --dry-run` and pre-commit checks). Never develop directly on `main`.
- **Merge and push to `main` when complete:** Do **not** open pull requests for changes in this repo. Once the worktree changes are tested and committed, merge the branch into `main`, remove the worktree (`wt remove`), and push `main`.

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
home/.chezmoiscripts/run_once_after_install-1password.sh.tmpl  # One-time install
```

- No executable bit needed — chezmoi handles this internally.
- Must include a `#!` shebang (chezmoi executes them via `exec(3)`).
- Must be idempotent.
- Tracked by git, **not** added via `chezmoi add` (source tree is protected).

### `.chezmoiscripts/` — one-time setup and package installation

Place non-config scripts in `.chezmoiscripts/` with prefixes like `run_once_`, `run_onchange_`, `run_before_`, `run_after_` for platform-specific one-off setup (package installs, credential setup, etc.). See [Use scripts to perform actions](https://chezmoi.io/user-guide/use-scripts-to-perform-actions/).

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

| Tool                   | Config / data location                            | How                                                                           |
| ---------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- |
| Terraform CLI          | `~/.config/terraform/terraformrc`                 | `TF_CLI_CONFIG_FILE` env var                                                  |
| Homebrew Brewfile      | `~/.config/brew/Brewfile`                         | `HOMEBREW_BUNDLE_FILE` env var                                                |
| zsh completions / dump | `~/.local/share/zsh/completions`, `~/.cache/zsh/` | explicit `fpath` + `compinit -d` in `.zshrc` (no framework; plugins from Nix) |
| atuin config           | `~/.config/atuin/`                                | Native XDG support                                                            |
| atuin data             | `~/.local/share/atuin/`                           | `db_path`/`key_path`/`session_path` in config                                 |
| atuin logs             | `~/.local/state/atuin/logs`                       | `[logs] dir =` in config                                                      |
| bat                    | `~/.config/bat/`                                  | Native XDG support                                                            |
| ghostty                | `~/.config/ghostty/`                              | Native XDG support                                                            |
| git                    | `~/.config/git/`                                  | Native XDG support                                                            |
| k9s                    | `~/.config/k9s/`                                  | Native XDG support                                                            |
| pnpm data              | `~/.local/share/pnpm/`                            | `PNPM_HOME` env var                                                           |
| Go data                | `~/.local/share/go/`                              | `GOPATH` env var                                                              |
| rclone                 | `~/.config/rclone/`                               | Native XDG support                                                            |
| terraform plugin cache | `~/.cache/terraform/`                             | `plugin_cache_dir` in config                                                  |
| tmux                   | `~/.config/tmux/`                                 | Native XDG support                                                            |
| zabrze                 | `~/.config/zabrze/`                               | Native XDG support                                                            |
| Zed                    | `~/.config/zed/`                                  | Native XDG support                                                            |
| zsh startup files      | `~/.config/zsh/{zshenv,zprofile,zshrc}`           | `ZDOTDIR` in bootstrap `~/.zshenv`                                            |
| Engram memory          | `~/.local/share/engram/`                          | `ENGRAM_DATA_DIR` env var                                                     |

### Intentionally non-XDG

These tools have no XDG support, or only a partial env-var workaround. Do not attempt to move them.

| Tool            | Location                              | Reason                                                                                                     |
| --------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SSH             | `~/.ssh/`                             | OpenSSH does not support XDG                                                                               |
| bash/sh startup | `~/.profile`, `~/.bash_profile`       | POSIX startup files; `.bash_profile` delegates to `.profile`; actual config in `~/.config/shell/env` (XDG) |
| omlx root       | `~/.omlx/`                            | Root dir hardcoded; only `model_dirs` is redirected to `~/.local/share/omlx/models`                        |
| Terraform data  | `~/.terraform.d/`                     | `TF_DATA_DIR` is per-workspace only; not safe to set globally                                              |
| Claude Code     | `~/.claude/`, `~/.claude.json`        | Other tools (e.g. Rex) hard-code `~/.claude`, so `CLAUDE_CONFIG_DIR` splits state                          |
| Pi agent        | `~/.pi/agent/`, `~/.pi/context-mode/` | Extensions hard-code `~/.pi`, so `PI_CODING_AGENT_DIR` splits state                                        |

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
- Add Pi plugins by declaring them in `.chezmoidata/pi.yaml` → `pi.packages`, then running `chezmoi apply` (the `run_after_pi-packages.py.tmpl` script reconciles the install automatically)

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

### CLI tools (both platforms): Nix

CLI tools are declared in `.chezmoidata/nix.yaml` → `nix.packages` (`base`/`personal`/`work`, plus `darwin.*` for macOS-only tools) as nixpkgs attribute names. `chezmoi apply` renders them into `~/.config/nix/packages/flake.nix` and `run_onchange_after_00-nix-packages.sh.tmpl` builds that flake into the `~/.local/state/nix/profiles/dotfiles` profile, whose `bin/` is on PATH ahead of Homebrew. Nix itself is installed by `run_once_before_install-nix.sh` (Determinate installer).

- nixpkgs is pinned by revision (`nix.nixpkgs_rev`); Renovate bumps it weekly. Unfree packages must be listed in `nix.unfree`.
- Roll back a bad bump with `nix profile rollback --profile ~/.local/state/nix/profiles/dotfiles`.
- **Package manager preference (all platforms): Nix > mise > Homebrew.** Tools missing from nixpkgs go to mise (`.chezmoitemplates/mise/base.toml` for every host, `darwin-personal.toml` for personal Macs; GitHub releases, PyPI via `pypi:`, etc.). Homebrew (macOS only) is the last resort: GUI apps and tools neither Nix nor mise can install (e.g. formulae that need build options).

### Linux

Beyond the Nix profile above, package management on Linux hosts is **out of band** — chezmoi does not install GUI apps or system packages on Linux; the user manages those with whatever tooling the distro provides (the system package manager, Flatpak, Distrobox, etc.).

- **Never install packages via Linuxbrew** — it has been removed from this repo; do not reintroduce it.
- The `.chezmoiscripts/linux/` scripts are generic — they run on any Linux distro (no distro-specific gating). Individual scripts may still guard themselves for a specific package manager (e.g. `apt-get`) and skip gracefully elsewhere.

### macOS

- CLI tools via Nix, then mise (above). `packages.yaml` → `darwin.brew.brews` holds only formulae neither can install.
- GUI apps via Homebrew Casks (or mas for Mac App Store apps).

#### Brew → Nix / mise policy

**Default to Nix for anything non-graphical, then mise; Homebrew is only for graphical apps and the exceptions below.** This covers formulae _and_ CLI-only casks (e.g. `1password-cli`, `claude-code`, `git-credential-manager`).

When adding a tool, or when reviewing `brew leaves` / `brew list --cask`:

1. Look for it in nixpkgs at the pinned rev (`nix eval --raw "github:NixOS/nixpkgs/<nix.nixpkgs_rev>#<attr>.meta.name"`). If it exists, add it to `.chezmoidata/nix.yaml` (`darwin.base` for tools that only ever lived in Homebrew; `base`/`personal`/`work` when Linux hosts want it too) and keep it out of `packages.yaml`.
2. Remove the Homebrew copy declaratively: add `formula:binary` (or `cask:binary` in the cask loop) to `run_onchange_after_05-brew-remove-nix-migrated.sh.tmpl`, and delete the entry from `darwin/packages.yaml`. Never `brew uninstall` by hand.
3. Not in nixpkgs: add it to `.chezmoitemplates/mise/` instead, and remove the Homebrew (or `uv`) copy via `run_onchange_after_06-brew-remove-mise-migrated.sh.tmpl`.
4. Drop a tap from `darwin.brew.taps` once its last formula/cask is gone.

Keep in Homebrew only when one of these holds:

- **GUI app** (`.app` casks), kernel extensions (`macfuse`), or Mac App Store apps (`mas`).
- **Not in nixpkgs and not installable by mise** (e.g. `omlx` with build options, `plist`, `utitool`).
- **Unfree and not in cache.nixos.org** — Nix would compile it from source (e.g. BUSL-licensed HashiCorp tools). Check with `nix path-info --store https://cache.nixos.org <outPath>` before moving anything unfree.
- **Needs a service definition we do not manage yet** (e.g. the `syncthing` launchd service). Move it only together with a chezmoi-managed LaunchAgent (see `colima`).

Toolchain managers replace the packages they manage: `rustup` supplies `cargo`/`rustc`/`rustfmt`/`clippy` proxies, so those are not listed separately in `nix.yaml` (they would collide in the profile); `run_onchange_after_01-rustup-toolchain.sh.tmpl` ensures a default toolchain.

The GUI/CLI split also applies to apps that ship both: keep the cask for the app (`mediainfo` GUI) and take the CLI from Nix (`mediainfo`).

## Further Reading

- [chezmoi Documentation](https://chezmoi.io/docs/)
- [Source Format](https://chezmoi.io/reference/source-formats/verbatim/)
- [External Sources](https://chezmoi.io/reference/external-sources/)
- [Using External Data](https://chezmoi.io/reference/data/)
- [State Management](https://chezmoi.io/docs/concepts/state/)
- [Recipes](https://chezmoi.io/recipes/) — community-contributed patterns
