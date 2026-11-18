# Private data

This repo is public. Values that identify an employer or its internal systems
(hostnames, repo and org names, accounts, MCP servers, AI gateway settings) are
kept out of the plaintext tree. Templates read them through one helper:

```gotemplate
{{ $p := includeTemplate "private-data" . | fromYaml }}
```

`.chezmoitemplates/private-data` returns the values for the current machine
class, merged over empty defaults, so every key exists on every machine. It
decrypts `home/.private/work.yaml.age` or `home/.private/personal.yaml.age`
(each encrypted to that class's age recipient) when age is configured
(`.encryption`), and returns only the defaults otherwise.

| Machine                 | Age identity                                                          |
| ----------------------- | --------------------------------------------------------------------- |
| Not headless            | `~/.local/share/chezmoi-age/identity.txt`, fetched from 1Password     |
| Workspace               | workspace secret `CHEZMOI_AGE_IDENTITY`, at `/run/user/$UID/secrets/` |
| Other headless machines | none: defaults only                                                   |

chezmoi ignores source entries whose names start with `.`, so `home/.private/`
never becomes a target.

### Workspaces

Workspaces have no 1Password. A work Mac uploads its age identity as the
workspace secret `CHEZMOI_AGE_IDENTITY` (not exported) in
`darwin/run_onchange_after_21-workspace-secrets.sh.tmpl`, and `.chezmoi.toml.tmpl`
turns on age when that file exists and the `age` binary (from the Nix profile)
is installed.

The workspaces CLI uploads secrets after it installs dotfiles, so the first
apply on a new workspace has no identity and renders the defaults. On the first
interactive login after the secret arrives, a hook in `.zshrc` runs
`chezmoi init --apply` once in the background (log:
`~/.local/state/chezmoi-first-login.log`). That apply re-renders `.zshrc`
without the hook.

## Keys

| Key                                                   | Used by                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `onepassword_account`                                 | `darwin/run_onchange_after_21-workspace-secrets.sh.tmpl`                                                            |
| `workspace_secrets.*`                                 | same                                                                                                                |
| `mcp_servers`, `mcp_workspace_exclude`, `mcp_retired` | `.chezmoitemplates/private-mcp-servers`, Pi `modify_mcp.json.tmpl`, `run_onchange_after_32-work-mcp-claude.sh.tmpl` |
| `claude.plugins`, `claude.remove_mcp`                 | `run_after_19-private-claude-plugins.sh.tmpl`                                                                       |
| `pi.packages`, `pi.local_repo`, `pi.local_packages`   | Pi `modify_settings.json.tmpl`, `run_after_pi-packages.py.tmpl`, `run_after_clone-work-pi-packages.sh.tmpl`         |
| `pi.gateway`                                          | Pi `modify_models.json.tmpl`                                                                                        |
| `trust_dirs`                                          | `.chezmoitemplates/trusted-dirs.tmpl`                                                                               |
| `git.nlopez_gitdirs`, `git.allowed_signers`           | `dot_config/git/config.tmpl`, `dot_config/git/allowed_signers.tmpl`                                                 |
| `gh_routes`                                           | `dot_config/gh/owner-accounts.tmpl` (read by `~/.local/bin/shims/gh`)                                               |
| `worktrunk_projects`                                  | `dot_config/worktrunk/config.toml.tmpl`                                                                             |
| `scan_patterns`                                       | `dot_config/dotfiles/private-patterns.txt.tmpl` (pre-commit hook)                                                   |
| `local_models.omlx_api_key`                           | Pi `extensions/local-models/config.ts.tmpl`                                                                         |
| `nix.packages`                                        | `.chezmoitemplates/nix-packages` (extra nixpkgs attributes for the Nix profile)                                     |

Add a new key to the defaults in `.chezmoitemplates/private-data` too.

## Edit

Machines with age configured keep a gitignored plaintext copy of their own
class's file next to the ciphertext: `home/.private/work.yaml` on work machines
and workspaces, `home/.private/personal.yaml` on personal machines. Read and
edit it directly; no decrypt step is needed.

`scripts/private-data-sync.sh` keeps the two in sync. It runs from chezmoi's
`read-source-state.pre` hook (so before every chezmoi command) and from the
`private-data-sync` pre-commit hook. It compares both sides against the last
synced content (a hash in `home/.private/.<class>.yaml.base`):

| Plaintext | Ciphertext | Result                                                                     |
| --------- | ---------- | -------------------------------------------------------------------------- |
| unchanged | changed    | plaintext is rewritten from the ciphertext (e.g. after `git pull`)         |
| edited    | unchanged  | ciphertext is re-encrypted; commit the `.age` file                         |
| edited    | changed    | conflict: nothing is touched, and the pre-commit hook fails until resolved |

The pre-commit hook also fails when it re-encrypts the file, so the new
ciphertext can be staged. To resolve a conflict, merge the changes into the
plaintext and encrypt it with the command the script prints.

From a machine of the other class, encrypt to that class's recipient with
`age -a -R ~/.local/share/chezmoi-age/<class>-recipient.txt`.

## Keep it clean

The `private-patterns` pre-commit hook (`scripts/check-private.sh`) rejects
staged plaintext that matches any regex in `~/.config/dotfiles/private-patterns.txt`.
The list itself names what it protects, so it lives in the private data
(`scan_patterns`) and is rendered only on work machines. Elsewhere the hook
warns and passes.
