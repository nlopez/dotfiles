# Agent Guidelines — Dotfile Management with Chezmoi

## What this repo is

A [chezmoi](https://chezmoi.io/) dotfile management repository for synchronizing dotfiles, configurations, and scripts across multiple machines. Chezmoi treats your home directory as immutable infrastructure version-controlled in Git.

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

| File | Contents |
|------|----------|
| [docs/getting-started.md](docs/getting-started.md) | What this repo is, setup, quick commands |
| [docs/core-concepts.md](docs/core-concepts.md) | Source state, `.chezmoiroot`, naming, templates, data, scripts |
| [docs/dotfile-workflows.md](docs/dotfile-workflows.md) | Adding/removing dotfiles, re-apply guarantee, boundaries |
| [docs/age-encryption.md](docs/age-encryption.md) | Age post-quantum encryption, key setup, secrets workflows |
| [docs/tools-and-validation.md](docs/tools-and-validation.md) | Linting, Pi plugin management, validation rules |
| [docs/quick-reference.md](docs/quick-reference.md) | Commands, repo navigation, path disambiguation |

## ⚠️ Boundaries

### ✅ Always do
- Edit via `chezmoi source-path <path>` or `chezmoi edit <path>`
- Verify with `chezmoi apply --dry-run` before committing
- Use templates for conditional logic (`.chezmoi.os`, `.chezmoi.arch`, etc.)
- Keep scripts idempotent — they must succeed even if already run
- Add Pi plugins through pnpm, never via `pi install`

### ⚠️ Ask first
- Change the `.chezmoiroot` file
- Modify the `.chezmoiignore` rules
- Change age encryption recipients or keys
- Remove a configuration deployed to multiple machines
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do
- Edit files directly in `~` — they will be overwritten on next `chezmoi apply`
- Append to live config files (e.g., `echo 'foo' >> ~/.zshrc`)
- Use `pi install <package>` — writes to destination, not source
- Commit secrets or credentials to the repo
- Bypass pre-commit hooks

## Further Reading

- [chezmoi Documentation](https://chezmoi.io/docs/)
- [Source Format](https://chezmoi.io/reference/source-formats/verbatim/)
- [External Sources](https://chezmoi.io/reference/external-sources/)
- [Using External Data](https://chezmoi.io/reference/data/)
- [State Management](https://chezmoi.io/docs/concepts/state/)
- [Recipes](https://chezmoi.io/recipes/) — community-contributed patterns
