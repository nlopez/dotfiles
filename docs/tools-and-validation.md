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

## Pi plugins — install via pnpm, not `pi install`

> ⚠️ **Pi does not self-update its own plugins.** The `pi install <package>` command writes directly to `~/.config/pi/settings.json` (the live destination file) and is **not** tracked by chezmoi. Packages installed this way will be lost on the next `chezmoi apply` and won't be reproduced on a fresh machine.

**Always add Pi plugins (extensions, skills, adapters) through pnpm** so they are version-controlled and automatically installed on every machine:

1. Add the package name to the `pnpm.personal` (or `pnpm.base`) list in
   `home/.chezmoidata/darwin/packages.yaml` (and the equivalent `linux/` file if needed).
2. Run `chezmoi apply` — the `run_onchange_after_pnpm-globals.sh.tmpl` script picks up the change and installs it globally via `pnpm add -g`.
3. Commit the data file change.

The MCP adapter for Pi (`pi-mcp-adapter`) follows the same rule and is declared in `packages.yaml` under `pnpm.personal`.

## ⚠️ Boundaries

### ✅ Always do
- Use `uv run scripts/jsonlint.py` before committing
- Run `pre-commit run --all-files` locally
- Add Pi plugins through pnpm, never via `pi install`

### ⚠️ Ask first
- Add a new linting step or tool
- Change pre-commit hook configuration
- Add a new external dependency via `.chezmoiexternal.toml`

### 🚫 Never do
- Commit files that fail linting
- Bypass pre-commit hooks
- Install packages directly to `~/.local/bin/` outside chezmoi
