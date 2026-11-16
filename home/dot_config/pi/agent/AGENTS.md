## Style Guide

### General Principles

- Before adding complexity for a speculative or vanishingly unlikely race or security edge case, explain the concrete failure mode, likelihood, and complexity cost to the user and get their buy-in. Do not silently expand scope for theoretical robustness.
- DO NOT leak our conversation, prompt, or iteration history into code comments, pull request descriptions, or other maintainer-facing prose. No "used to be X, now Y", "changed from", "per the user's request", or similar. Comments describe the code as it is, and only when the why is non-obvious.
- Never add AI attribution to commits, PR bodies, or issues: no `Co-Authored-By` trailers, no "Generated with Claude Code" lines, and no "Co-authored with Claude" footers.

### Git signing and hooks

- Every commit must be signed and every git hook must run. Never use `--no-verify`, `-n` on `git commit`, `--no-gpg-sign`, `-c commit.gpgsign=false`, `git config commit.gpgsign false`, `GIT_CONFIG_*` overrides, or any other way to skip hooks or signing.
- If signing fails (for example, 1Password is locked or `op-ssh-sign` errors) or a hook rejects the commit or push, stop and report the exact error to the user. Do not retry with signing or hooks disabled.

### Git worktrees

- A worktree's directory and its checked-out branch must always match. Never `git switch`/`checkout` (including `checkout -b`) to a different branch inside any worktree. `main`/`default` is shared by other sessions, but the rule applies everywhere.
- To work on another branch, use or create that branch's own worktree (`wt switch --create <branch>`).
- Before every commit or push, run `git branch --show-current` and confirm it matches the worktree directory name.
