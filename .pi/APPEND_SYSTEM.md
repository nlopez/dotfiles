## Source-of-Truth Rule

**Never edit files directly in `~` or any destination path.** This repo is a [chezmoi](https://chezmoi.io/) dotfile management repository. All config changes must go through the source tree.

1. `chezmoi source-path <destination>` to find the source file
2. Edit in the source tree (`.local/share/chezmoi/home/...`)
3. Validate with `chezmoi diff` and `chezmoi apply --dry-run`
4. Apply with `chezmoi apply`

If you are unsure whether a file is managed by chezmoi, assume it is. See AGENTS.md for full guidelines.
