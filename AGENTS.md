# Agent Guidelines — chezmoi dotfiles

`~` is derived, never edited. Every change is declared in the source tree (`home/`, see
`.chezmoiroot`) and materialized by `chezmoi apply`. Never run `brew install`, `pi install`,
`npm install`, or `echo >> ~/.zshrc` as a standalone action — declare it, then apply.

## Workflow

- `chezmoi-fast <cmd>` (`CHEZMOI_SKIP_SECRETS=1`) by default. Plain `chezmoi` only when the
  change touches secrets or age-encrypted files.
- Edit via `chezmoi edit <path>` / `chezmoi source-path <path>`; verify with `--dry-run`.
- In a worktree, chezmoi still reads `~/.local/share/chezmoi`: pass `-S <worktree root>` to
  `diff` and `apply --dry-run`. Never `apply` from a worktree; `~` is shared.
- Commit and push `main` when done. No PRs, no bypassed hooks.
- Release from a worktree branch, without asking: `git fetch origin && git rebase origin/main`,
  then `git push origin HEAD:main` (fast-forward only; if rejected, fetch, rebase, retry). Don't
  push the branch itself; if it was pushed, `git push origin --delete <branch>`. Then run
  `chezmoi-fast update` to pull the main checkout and apply. Leave the worktree in place and
  tell the user to run `wt remove <branch>` from the main checkout.
- `modify_*` files are scripts. Rendered-template output needs `chezmoi:modify-template` and
  no `.tmpl` suffix.
- Pi plugins: declare in `.chezmoidata/pi.yaml` → `packages`, then `chezmoi apply`.

## Scripts

`home/.chezmoiscripts/` (`darwin/`, `linux/` for OS-specific): `run_after_*` every apply,
`run_onchange_after_*` when content changes, `run_once_*` once. Needs a shebang, must be
idempotent, tracked by git (not `chezmoi add`). Never invoke `chezmoi` from a hook.

## Packages

Nix > mise > Homebrew. CLI tools go in `.chezmoidata/nix.yaml`; not in nixpkgs →
`.chezmoitemplates/mise/`. Homebrew (macOS only) for GUI apps, Mac App Store (`mas`), kernel
extensions, and things neither can install (or unfree packages missing from
cache.nixos.org). To retire a Homebrew package, delete it from
`.chezmoidata/darwin/packages.yaml`; `brew.cleanup` uninstalls anything undeclared on apply
(`chezmoi diff` lists it first), never `brew uninstall`. Linux system packages are out of
band; no Linuxbrew.

## 1Password

Personal macOS: `op` reads use a read-only service account (`~/.local/bin/shims/op`), no
prompt. Templates read secrets with
`output (joinPath .chezmoi.workingTree "scripts/op-automation.sh") "read" "--no-newline" "op://…"`,
never `onepasswordRead` (it runs `op signin`). Reference items by UUID, not name (`Automation`
vault `evjh25ux2mnoufaut6qhvm2pdi`). Writes and app auth: `OP_APP_AUTH=1 op …`. Work machines:
`op signin` first.

## Pending work

On a work host, check `docs/todo.md` for tasks only that machine class can do.

## Ask first

`.chezmoiroot`, `.chezmoiignore`, age recipients or keys, removing config deployed to several
machines, a new `.chezmoiexternal.toml` dependency.

## Never

Edit or append to files in `~`; commit secrets; run `pi install` by hand; bypass hooks.

Reference detail lives in `docs/` (getting-started, core-concepts, dotfile-workflows,
age-encryption, tools-and-validation, quick-reference).
