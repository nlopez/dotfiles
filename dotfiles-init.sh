#!/usr/bin/env bash
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null

if [ ! -d "$HOME/.dotfiles" ]; then
    git clone --bare https://github.com/nlopez/dotfiles "$HOME/.dotfiles"
fi


function dotfiles {
   /usr/bin/git --git-dir="$HOME/.dotfiles/" --work-tree="$HOME" "$@"
}

backup_dir="$HOME/dotfiles-backup/$(date +%Y-%m-%d--%H-%M-%S)"
mkdir -p "$backup_dir"

# dotfiles ls-tree --full-tree -r --name-only HEAD

while IFS= read -r -d '' file; do
    if [ -f "$HOME/$file" ] || [ -d "$HOME/$file" ]; then
        echo "Backing up pre-existing dotfile: $file"
        mkdir -p "$backup_dir/$(dirname "$file")"
        mv "$HOME/$file" "$backup_dir/$file"
    fi
done < <(dotfiles ls-tree --full-tree -r --name-only -z HEAD)

dotfiles switch --discard-changes main

# backup_dir="$HOME/.dotfiles-backup-$(date +%Y-%m-%d--%H-%M-%S)"
# mkdir -p "$backup_dir"
# if dotfiles checkout; then
#   echo "Checked out dotfiles."
#   else
#     echo "Backing up pre-existing dotfiles."
#     dotfiles checkout 2>&1 | grep -E "\s+\." | awk '{print $1}' | xargs -I {} mv {} "$backup_dir"/{}
# fi

# dotfiles checkout
dotfiles config status.showUntrackedFiles no
