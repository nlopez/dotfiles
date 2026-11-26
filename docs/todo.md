# Pending work

Tasks that must run on a specific machine class. Remove an entry once it is done.

## Work hosts

### Drop `engram_cloud.projects` from `work.yaml.age`

Nothing reads the key anymore: `~/.local/bin/engram-cloud-enroll` enrolls every
project under `~/src` and in the local Engram store. Only a work host can
decrypt the file (the work age key is in the work 1Password account).

```sh
cd ~/.local/share/chezmoi/home/.private
chezmoi decrypt work.yaml.age | yq 'del(.engram_cloud.projects)' | chezmoi encrypt >work.yaml.age.new
mv work.yaml.age.new work.yaml.age
chezmoi decrypt work.yaml.age | yq '.engram_cloud | keys' # projects is gone
git add work.yaml.age
git commit -m "private: drop unused engram_cloud.projects"
```

Then delete this entry and push.
