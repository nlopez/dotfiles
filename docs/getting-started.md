# Getting Started with Chezmoi

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

## Quick commands

```sh
chezmoi apply --dry-run          # Preview changes
chezmoi status                   # Diff source vs destination
chezmoi diff                     # Show what would change
chezmoi add ~/.config/foo/bar    # Add a new file
chezmoi edit ~/.config/foo/bar   # Edit via source tree
```
