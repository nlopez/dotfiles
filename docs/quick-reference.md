# Quick Reference

## Useful Chezmoi Commands

| Command                         | Purpose                                          |
|---------------------------------|--------------------------------------------------|
| `chezmoi apply`                 | Apply all dotfiles to current machine             |
| `chezmoi apply --dry-run`       | Preview changes without applying                  |
| `chezmoi apply --dry-run --verbose` | Preview changes with full detail            |
| `chezmoi status`                | Show source vs. destination differences           |
| `chezmoi diff`                  | Show what would change on apply                   |
| `chezmoi add <path>`            | Add a file/dir to source state                    |
| `chezmoi edit <path>`           | Edit a source file (creates it if missing)        |
| `chezmoi forget <path>`         | Remove a file from source state                   |
| `chezmoi source-path <path>`    | Resolve a destination path to its source file     |
| `chezmoi data`                  | Print the merged data map for template debugging  |
| `chezmoi cat <path>`            | Show rendered output of a source file             |

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

## Path disambiguation

| What you want | Where it lives |
|---------------|---------------|
| This file (`AGENTS.md`) | Repo root: `AGENTS.md` |
| chezmoi scripts | `home/.chezmoiscripts/` (NOT repo root `scripts/`) |
| Lint scripts | Repo root: `scripts/` (NOT chezmoi-managed) |
| The `.chezmoiroot` file | Repo root: `.chezmoiroot` |
| Source for `~/.gitconfig` | `home/dot_gitconfig` |
| Source for `~/.config/tmux/` | `home/dot_config/tmux/` |
