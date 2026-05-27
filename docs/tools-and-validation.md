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

## Pi packages (npm) — declare in `modify_settings.json`

Pi npm packages (extensions, skills, adapters) are managed via the `packages` key in
`~/.pi/agent/settings.json`. The source of truth is the `required_packages` list in
`home/dot_pi/agent/modify_settings.json` — a chezmoi `modify_` Python script that reads
`settings.json` from stdin and writes the merged JSON to stdout on every `chezmoi apply`.

**To add or update a Pi npm package:**

1. Add `"npm:<package>@<version>"` to the `required_packages` list in
   `home/dot_pi/agent/modify_settings.json`.
2. Run `chezmoi apply` — the modify script writes the package into `settings.json`.
3. Install the package at runtime: `pi install npm:<package>@<version>`.
4. Commit the source change.

Pi npm packages are **not** pnpm globals. They live in `~/.pi/agent/npm/` and are
managed by `pi install`, not `pnpm add -g`. Do not add them to `pnpm.yaml`.

## pnpm globals — declare in `pnpm.yaml`

Standalone CLI tools that need to be on `PATH` (e.g., `mmd`, `pi-coding-agent`)
are installed as pnpm globals. Add them to the `pnpm.base` list in
`home/.chezmoidata/pnpm.yaml`.

The `run_onchange_after_pnpm-globals.sh.tmpl` script reads `pnpm.yaml` and runs
`pnpm add -g` for each entry on every `chezmoi apply`.

## ⚠️ Boundaries

### ✅ Always do

- Use `uv run scripts/jsonlint.py` before committing
- Run `pre-commit run --all-files` locally
- Declare Pi npm packages in `modify_settings.json`, not `pnpm.yaml`
- Declare pnpm globals in `pnpm.yaml`, not `modify_settings.json`
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
- Use `pi install` to declare new packages — it writes to destination only. First add to `modify_settings.json` (Pi plugins) or `pnpm.yaml` (pnpm globals), then `chezmoi apply` and `pi install`.
- Add Pi npm packages to `pnpm.yaml` — they must go in `modify_settings.json`.
