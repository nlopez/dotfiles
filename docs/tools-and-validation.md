# Tools, Linting & Validation

## Linting / Validation

Project linting is automated via pre-commit hooks and custom scripts. Ensure all changes pass validation before committing:

```sh
# Shellcheck all .sh and .sh.tmpl files in .chezmoiscripts/
uv run scripts/shellcheck.py

# Run all pre-commit hooks (gitleaks, ruff, prettier, shellcheck, agent-guards, yamlfmt)
pre-commit run --all-files
```

## Pi packages (npm) — declare in `.chezmoidata/pi.yaml`

Pi npm packages (extensions, skills, adapters) are declared in `pi.packages` in
`home/.chezmoidata/pi.yaml`. `modify_settings.json.tmpl` and
`run_after_pi-packages.py.tmpl` read that list at render time.

**To add or update a Pi npm package:**

1. Add `"npm:<package>@<version>"` to `pi.packages` in `home/.chezmoidata/pi.yaml`.
2. Run `chezmoi apply`. chezmoi writes the declaration to `settings.json`, then
   `run_after_pi-packages.py.tmpl` makes the installs match it: it writes Pi's
   `npm/package.json` with exactly the declared npm packages, runs `npm install`
   (which removes everything else), and deletes undeclared git clones.
3. Commit the source change.

`pi.yaml` is the whole package list. The script runs on every apply, so packages
installed by hand (`pi install`, `npm install`) are removed on the next `chezmoi apply`.

## Datadog skills — not installed

The 61 skills from [datadog-labs/agent-skills](https://github.com/datadog-labs/agent-skills)
aren't installed. They're cheat-sheets for the `pup` CLI (51 of them only spell out
`pup <domain> <cmd>`), and their descriptions are resident in every prompt. Use
`pup <domain> --help` instead. To bring them back on demand:

```sh
pup skills list && pup skills install      # from the pup binary
# or: cp -r datadog-labs/agent-skills/<skill> ~/.pi/agent/skills/
```

The `dd-pup` extension (the pup CLI as pi tools) is installed, unlike the skills:
`run_onchange_after_04-pup-skills.sh.tmpl` runs `pup skills install pi --name=dd-pup-pi`
and re-runs when the pup version in `mise/base.toml` changes.

## ⚠️ Boundaries

### ✅ Always do

- Run `pre-commit run --all-files` locally
- Declare Pi npm packages in `.chezmoidata/pi.yaml`
- Follow chezmoi `modify_` semantics: plain `modify_*` files are scripts; only use
  `chezmoi:modify-template` when the rendered template output should become the final file;
  modify templates must not have a `.tmpl` suffix

### ⚠️ Ask first

- Add a new linting step or tool
- Change pre-commit hook configuration
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do

- Commit files that fail linting
- Bypass pre-commit hooks
- Install packages directly to `~/.local/bin/` outside chezmoi
- Install anything via `pnpm add -g` (pnpm globals) — this repo does not manage global pnpm packages
- Run `pi install` directly to add packages — declare them in `.chezmoidata/pi.yaml` and let `chezmoi apply` install them.
