## GitHub Content

Always use the `gh` CLI to fetch GitHub content — repos, files, issues, pull requests, releases, and GitHub-hosted docs. `gh` is authenticated, structured, and rate-limit-safe. Never use web fetch tools or manual API calls for github.com URLs.

## Package Management

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

## Research and Uncertainty Protocol

When you are uncertain about something, or when official documentation and best practices would help you make a better decision, **you must search for authoritative sources before guessing**.

### When to search

- You are unsure about a library's API, configuration, or behavior
- You want to follow current best practices for a task
- You are working with unfamiliar code, tools, or frameworks
- You need to verify how something works rather than assume
- The user asks for recommendations or guidance on how to do something

### How to search

1. **Start with web search** for official docs, release notes, and community best practices. Prefer official documentation over third-party blog posts.
2. **Use the `gh` CLI for anything on github.com** — repos, issues, pull requests, code, releases, and GitHub-hosted docs. `gh` is authenticated, structured, and rate-limit-safe. **Never use `fetch_content`, `web_search`, or manual API calls for github.com URLs.**
   - **For searching or reading files across a repo, clone it locally first** with `gh repo clone <owner>/<repo> /tmp/<repo> -- --depth=1 --quiet`, then use standard tools (`grep`, `find`, `read`). Do not make repeated `gh search code` calls — the GitHub search API is aggressively rate-limited and returns incomplete results. A shallow clone is faster, exhaustive, and not rate-limited.
   - Reserve `gh search code` only for a single targeted lookup where cloning would be wasteful (e.g., checking one specific string across all of GitHub).
3. **Use `fetch_content` for non-GitHub URLs** — documentation sites, blog posts, or other web pages with deeper context.

### Key principle

**When in doubt, search it out.** It is better to take a moment to find authoritative guidance than to guess and produce a suboptimal or incorrect solution. Always cite your sources when referencing docs or guidance you looked up.

## Editing Files

Pi's `edit` tool matches `oldText` against the file's current bytes. Fuzzy matching is applied automatically for line endings, trailing whitespace, smart quotes, Unicode dashes, and special spaces — but **not** for leading indentation or hallucinated content. "Could not find the exact text" almost always means the model is editing from a stale or imagined view of the file. Follow these rules to avoid wasted retries and partial edits:

- **Read before edit.** `read` the file (or the relevant region with `offset`/`limit`) in the same turn as the `edit`. Never edit from memory if the file was last read more than a few turns ago, or if any other tool may have changed it since.
- **Keep `oldText` minimal.** 1–5 lines, just enough to be unique. Avoid pasting whole functions or large blocks — every extra line is another chance to mismatch on whitespace you only half-remember.
- **Anchor on content, not indentation.** When you cannot be certain of leading whitespace, choose an `oldText` that is unique on its trimmed content. Fuzzy match handles trailing whitespace, not leading indentation.
- **Batch disjoint edits in one call.** Use multiple entries in `edits[]` for separate changes to the same file. Do not chain many separate `edit` calls when one will do.
- **One retry, then re-read.** If `edit` fails with "Could not find the exact text", do not retry the same `oldText` more than once. Re-`read` the affected region first, then issue a corrected edit.
- **Prefer `write` for large rewrites.** When a change touches more than ~3 distinct regions, or restructures a file, rewrite the whole file with `write` instead of stacking `edit` calls.
- **After compaction, treat all files as stale.** If history was compacted this session, `read` any file again before editing it.
