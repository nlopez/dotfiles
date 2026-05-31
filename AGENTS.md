# Agent Guidelines — Dotfile Management with Chezmoi

## What this repo is

A [chezmoi](https://chezmoi.io/) dotfile management repository for synchronizing dotfiles, configurations, and scripts across multiple machines. **The goal of this repo is to maintain a fully declarative configuration that works identically on any machine.**

Chezmoi treats your home directory as immutable infrastructure version-controlled in Git — every file in `~` should be reproducible from the source tree alone. This means:

- **No manual edits** — never edit files directly in `~`; always go through the chezmoi source tree.
- **Idempotent & portable** — any machine can run `chezmoi apply` and end up with an identical, working configuration.
- **Declarative over imperative** — prefer static templates (`.tmpl`) with `.chezmoi.os`/`.chezmoi.arch` conditionals over shell scripts. Scripts belong in `.chezmoiscripts/` only for one-time setup that can't be expressed as config files.
- **Source of truth lives in Git** — the source tree under `home/` is the single source of truth. The destination (`~`) is ephemeral and always derived from it.

## Quick setup

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- init <owner>/<repo>
chezmoi apply
```

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
├── scripts/                       # Project scripts (linting, not chezmoi-managed)
└── .chezmoiroot                   # Value: home
```

## Full documentation

| File                                                         | Contents                                                       |
| ------------------------------------------------------------ | -------------------------------------------------------------- |
| [docs/getting-started.md](docs/getting-started.md)           | What this repo is, setup, quick commands                       |
| [docs/core-concepts.md](docs/core-concepts.md)               | Source state, `.chezmoiroot`, naming, templates, data, scripts |
| [docs/dotfile-workflows.md](docs/dotfile-workflows.md)       | Adding/removing dotfiles, re-apply guarantee, boundaries       |
| [docs/age-encryption.md](docs/age-encryption.md)             | Age post-quantum encryption, key setup, secrets workflows      |
| [docs/tools-and-validation.md](docs/tools-and-validation.md) | Linting, Pi plugin management, validation rules                |
| [docs/quick-reference.md](docs/quick-reference.md)           | Commands, repo navigation, path disambiguation                 |

## ⚠️ Boundaries

### ✅ Always do

- Edit via `chezmoi source-path <path>` or `chezmoi edit <path>`
- Verify with `chezmoi apply --dry-run` before committing
- Use templates for conditional logic (`.chezmoi.os`, `.chezmoi.arch`, etc.)
- Keep scripts idempotent — they must succeed even if already run
- For chezmoi `modify_` files, follow target-type semantics: plain `modify_*` files are
  scripts; only use `chezmoi:modify-template` when rendered template output should become
  the final file contents; modify templates must not have a `.tmpl` suffix
- Add Pi plugins via `modify_settings.json` and `pi install`, not as pnpm globals

### ⚠️ Ask first

- Change the `.chezmoiroot` file
- Modify the `.chezmoiignore` rules
- Change age encryption recipients or keys
- Remove a configuration deployed to multiple machines
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do

- Edit files directly in `~` — they will be overwritten on next `chezmoi apply`
- Append to live config files (e.g., `echo 'foo' >> ~/.zshrc`)
- Use `pi install` as the declaration mechanism for Pi plugins. First declare them in `modify_settings.json`, then run `chezmoi apply` and `pi install`.
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
