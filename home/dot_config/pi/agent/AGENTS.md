## Style Guide

### General Principles

- Before adding complexity for a speculative or vanishingly unlikely race or security edge case, explain the concrete failure mode, likelihood, and complexity cost to the user and get their buy-in. Do not silently expand scope for theoretical robustness.
- Never add AI attribution to commits, PR bodies, or issues: no `Co-Authored-By` trailers, no "Generated with Claude Code" lines, and no "Co-authored with Claude" footers.

### Git worktrees

- A worktree's directory and its checked-out branch must always match. Never `git switch`/`checkout` (including `checkout -b`) to a different branch inside any worktree. `main`/`default` is shared by other sessions, but the rule applies everywhere.
- To work on another branch, use or create that branch's own worktree (`wt switch --create <branch>`).
- Before every commit or push, run `git branch --show-current` and confirm it matches the worktree directory name.
