# Dotfile Workflows

## Adding a new dotfile

1. Create the file in the repo using the naming convention (`dot_<name>`, `config/...`, `bin/...`).
2. If it needs templating or data-driven values, use a `.tmpl` extension and reference data from `.chezmoidata/`.
3. Add it to `.chezmoiignore` only if it should exist in source but not be deployed to certain platforms.
4. Run `chezmoi apply --dry-run` to verify, then commit.

## Removing configurations

Chezmoi only looks at the **current** state of the source tree — it has no history, so deleting a source file does **not** remove the file from `~` on machines where it was previously applied ([discussion #1446](https://github.com/twpayne/chezmoi/discussions/1446)). You must explicitly tell chezmoi to remove the destination path.

### Removal steps

1. **Remove the source entry** — delete the `dot_<name>`, `config/...`, or `bin/...` source file/dir from the repo.
2. **Declare the destination removal** — pick the most idiomatic mechanism:
   - **`home/.chezmoiremove` (preferred)** — a [template](https://chezmoi.io/user-guide/manage-different-types-of-file/#ensure-that-a-target-is-removed) listing destination paths (relative to `~`, no leading `~/`) that chezmoi must ensure do not exist. Runs on every `chezmoi apply`, idempotent, supports glob patterns and template conditionals. Use this for any path chezmoi previously managed. Leave the entry in place until every machine has applied at least once; then it can be pruned.
   - **`remove_<name>` source attribute** — declares a single source entry that should not exist at the destination. Useful when you also want to keep a placeholder in the source tree, but for plain "this path must be gone" cleanup, `.chezmoiremove` is simpler and centralised.
   - **`run_once_after_remove-*.sh` cleanup script** — only when removal needs imperative logic that `.chezmoiremove` cannot express (e.g., rewriting another tool's state file, unsetting a fish universal variable, calling a package manager). Not for plain file deletion.
3. **Clean up ancillary artifacts** — if the config created data dirs, symlinks, or registered itself with another tool, list them in `.chezmoiremove` too, or add a `run_once_after_remove-*.sh` script for non-file cleanup.
4. **Drop `empty_` markers** — if you created them only to suppress chezmoi recreating a path, remove them once cleanup has landed everywhere. (Note: there is no `dir_` prefix in chezmoi; directory sources are created by adding an empty directory to the source tree.)

Verify with `chezmoi apply --dry-run --verbose` before committing, and `chezmoi apply` to clear the local machine.

This ensures that re-applying chezmoi on a machine that previously had the old config ends up in a clean state rather than leaving stale artifacts.

## Re-apply guarantee

**`chezmoi apply` must be a safe, complete reset.** Re-running it should:

- Recreate all managed files to match the source tree
- Not break any tools that depend on the config
- Leave no orphaned files from removed configs
- Produce the same result regardless of how many times it's run

Before committing any change, ask: "If I wiped my home directory and ran `chezmoi apply` from scratch, would everything work?" If the answer is no, the change needs cleanup scripts, empty/dir markers, or additional template guards.

## ⚠️ Boundaries

### ✅ Always do

- Edit via `chezmoi source-path <path>` or `chezmoi edit <path>`
- Verify with `chezmoi apply --dry-run` before committing
- Use templates for conditional logic (`.chezmoi.os`, `.chezmoi.arch`, etc.)
- Keep scripts idempotent — they must succeed even if already run

### ⚠️ Ask first

- Change the `.chezmoiroot` file
- Modify the `.chezmoiignore` rules
- Change age encryption recipients or keys
- Remove a configuration that's deployed to multiple machines

### 🚫 Never do

- Edit files directly in `~` — they will be overwritten on next `chezmoi apply`
- Append to live config files (e.g., `echo 'foo' >> ~/.zshrc`)
- Use `pi install <package>` — writes to destination, not source
- Commit secrets or credentials to the repo
