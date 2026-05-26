# Tools, Linting & Validation

## Linting / Validation

Project linting is automated via pre-commit hooks and custom scripts. Ensure all changes pass validation before committing:

```sh
# Lint all JSON templates (renders for darwin/linux/windows)
uv run scripts/jsonlint.py

# Shellcheck all .sh and .sh.tmpl files in .chezmoiscripts/
uv run scripts/shellcheck.py

# Run all pre-commit hooks (gitleaks, yamlfmt, jsonlint, shellcheck)
pre-commit run --all-files
```

## Pi packages (npm) — declare in `modify_settings.json`

Pi npm packages (extensions, skills, adapters) are managed via the `packages` key in
`~/.pi/agent/settings.json`. The source of truth is the `required_packages` list in
`home/dot_pi/agent/modify_settings.json` — a Python template that merges pinned versions
into `settings.json` on every `chezmoi apply`.

**To add or update a Pi npm package:**

1. Add `"npm:<package>@<version>"` to the `required_packages` list in
   `home/dot_pi/agent/modify_settings.json`.
2. Run `chezmoi apply` — the template writes the package into `settings.json`.
3. Install the package at runtime: `pi install npm:<package>@<version>`.
4. Commit the template change.

Pi npm packages are **not** pnpm globals. They live in `~/.pi/agent/npm/` and are
managed by `pi install`, not `pnpm add -g`. Do not add them to `pnpm.yaml`.

## pnpm globals — declare in `pnpm.yaml`

Standalone CLI tools that need to be on `PATH` (e.g., `mmd`, `pi-coding-agent`,
`pi-web-access`) are installed as pnpm globals. Add them to the `pnpm.base` list in
`home/.chezmoidata/pnpm.yaml`.

The `run_onchange_after_pnpm-globals.sh.tmpl` script reads `pnpm.yaml` and runs
`pnpm add -g` for each entry on every `chezmoi apply`.

## ⚠️ Boundaries

### ✅ Always do
- Use `uv run scripts/jsonlint.py` before committing
- Run `pre-commit run --all-files` locally
- Declare Pi npm packages in `modify_settings.json`, not `pnpm.yaml`
- Declare pnpm globals in `pnpm.yaml`, not `modify_settings.json`

### ⚠️ Ask first
- Add a new linting step or tool
- Change pre-commit hook configuration
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do
- Commit files that fail linting
- Bypass pre-commit hooks
- Install packages directly to `~/.local/bin/` outside chezmoi
