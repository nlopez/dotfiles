# Tools, Linting & Validation

## Linting / Validation

Project linting is automated via pre-commit hooks and custom scripts. Ensure all changes pass validation before committing:

```sh
# Lint all JSON templates (renders for darwin/linux)
uv run scripts/jsonlint.py

# Shellcheck all .sh and .sh.tmpl files in .chezmoiscripts/
uv run scripts/shellcheck.py

# Run all pre-commit hooks (gitleaks, yamlfmt, jsonlint, shellcheck)
pre-commit run --all-files
```

## Pi packages (npm) — declare in `.chezmoidata/pi.yaml`

Pi npm packages (extensions, skills, adapters) are declared in `pi.packages` in
`home/.chezmoidata/pi.yaml`. `modify_settings.json.tmpl` and
`run_onchange_after_pi-packages.py.tmpl` read that list at render time.

**To add or update a Pi npm package:**

1. Add `"npm:<package>@<version>"` to `pi.packages` in `home/.chezmoidata/pi.yaml`.
2. Run `chezmoi apply` — the `run_onchange_after_pi-packages.py.tmpl` hook reconciles the install.
3. Commit the source change.

Pi npm packages are managed by `pi install`, not `pnpm add -g`. Nothing is installed
as a pnpm global in this repo — chezmoi does not run `pnpm add -g` for anything.

## ⚠️ Boundaries

### ✅ Always do

- Use `uv run scripts/jsonlint.py` before committing
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
