## GitHub Content

Always use the `gh` CLI to fetch GitHub content — repos, files, issues, pull requests, releases, and GitHub-hosted docs. `gh` is authenticated, structured, and rate-limit-safe. Never use web fetch tools or manual API calls for github.com URLs.

## Git Cloning and Worktrees

Clone with **`ghq get <owner>/<repo>`** (or a full URL). It clones to
`~/src/<host>/<owner>/<repo>`.
`ghq list -p` lists local clones.

Worktrees come from **worktrunk (`wt`)** only; never run `git worktree add` directly.
They live under `~/src/.worktrees/<owner>/<repo>.<branch>`. Claude Code (`claude -w`)
creates its worktrees through `wt` too.

```sh
wt switch --create <branch>   # new worktree + branch
wt switch <branch>            # existing worktree
wt list
wt remove                     # remove worktree (deletes branch if merged)
```

One task, one branch, one worktree. Remove it once merged.

Always prefer **`uv`** for Python and **`pnpm`** for Node.js.

- Python: use `uv pip install`, `uv run`, `uv build` for project work; use `uv tool install` to install tools globally (the equivalent of `pip install --system` or `pipx`). Prefer `uvx <tool>` to run installed tools without pinning them.
- Node.js: use `pnpm install`, `pnpm run`, `pnpm exec` for project work; use `pnpm dlx` to run one-off packages (the equivalent of `npx`). Always pin versions when possible.

Never use `pip`, `python -m pip`, `npm`, or `yarn` directly. If `uv` or `pnpm` are not available on the system, note the limitation and fall back.

## Cloud Profile Safety Rule

**You must never use a cloud profile whose name does not end in `read-only`.** This applies universally to every tool and surface where a profile can be specified:

- `AWS_PROFILE` / `AWS_DEFAULT_PROFILE` environment variables
- `--profile` flag on `aws` commands
- `AWS_PROFILE` set inside Terraform / OpenTofu provider blocks or via `-var`/`TF_VAR_*`
- Terragrunt `iam_role`, `iam_assume_role_duration`, or any profile reference in `terragrunt.hcl`
- Any other CLI tool (`awsume`, `awsv`, `awsx`, `yawsso`, etc.) that accepts an AWS or cloud profile name

Before running any command or writing any config that references a profile, check that the profile name ends with `read-only`. If the desired profile does not end in `read-only`, **stop and tell the user** rather than proceeding.
