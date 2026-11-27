#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_claude/executable_statusline.py
# Claude Code status line modelled on pi's powerline footer:
#   model | think:<effort> | dir <name> | ⎇ <branch> | PR #12 ✓ approved | PRs #9 ✗ · repo#4 merged
#   | ▥ used/size (pct%) AC | (sub)
# `--no-prs` drops the PR parts. PR data comes from ~/.config/argus-pr/pr_tracking.py
# (cached `gh pr view`, refreshed in the background).
# PR labels are OSC 8 hyperlinks to the PR. In Rex they move to a tiled
# pane on the right of Claude's pane (~/.config/argus-pr/pr_float.py).
# Claude pipes a JSON blob on stdin; whatever we print is the status line.
import contextlib
import getpass
import json
import os
import socket
import sys

sys.path.insert(0, os.path.expanduser("~/.config/argus-pr"))
import pr_float  # noqa: E402
import pr_tracking  # noqa: E402
from pr_tracking import BLUE, CYAN, DIM, GREEN, MAGENTA, WHITE, c, git  # noqa: E402


def tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".removesuffix(".0") + "M"
    if n >= 1000:
        return f"{n / 1000:.1f}".removesuffix(".0") + "k"
    return str(n)


def pr_parts(data, cwd, common, branch):
    # In Rex, pr_float.py shows the PRs in a tiled pane instead.
    block = os.environ.get("REX_BLOCK")
    if block and pr_float.running(block):
        return []
    here = os.path.basename(os.path.dirname(common)) if common else ""
    found = pr_tracking.prs(data.get("session_id"), cwd, common, branch)
    parts = [f"{c(WHITE, 'PR')} {pr_tracking.label(pr)}" for pr, current in found if current]
    others = [pr for pr, current in found if not current]
    labels = []
    for pr in others[-3:]:
        repo = pr_tracking.repo_of(pr["url"])
        labels.append(pr_tracking.label(pr, "" if repo == here else repo))
    if labels:
        more = c(DIM, f" +{len(others) - 3}") if len(others) > 3 else ""
        parts.append(f"{c(WHITE, 'PRs')} " + c(DIM, " · ").join(labels) + more)
    return parts


def dir_part(cwd, common, git_dir, top):
    # Linked worktrees (`claude -w`) get random directory names, so show the
    # main repo's name instead, plus any subdirectory below the worktree root.
    if common and git_dir and common != git_dir and top:
        name = os.path.basename(os.path.dirname(common.rstrip("/")))
        rel = os.path.relpath(os.path.realpath(cwd), os.path.realpath(top))
        if rel != ".":
            name = f"{name}/{rel}"
        return c(CYAN, f"dir {name}") + c(DIM, " (worktree)")
    return c(CYAN, f"dir {os.path.basename(cwd.rstrip('/')) or '/'}")


def auto_compact_on():
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    path = os.path.join(config_dir, ".claude.json") if config_dir else os.path.expanduser("~/.claude.json")
    try:
        with open(path) as f:
            return json.load(f).get("autoCompactEnabled", True)
    except Exception:
        return True


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    cwd = data.get("workspace", {}).get("current_dir") or data.get("cwd") or os.getcwd()
    sep = c(DIM, " | ")
    parts = []

    # Like the zsh prompt (pure): user@host first, always shown.
    with contextlib.suppress(Exception):
        parts.append(c(DIM, f"{getpass.getuser()}@{socket.gethostname().split('.')[0]}"))

    model = data.get("model", {}).get("display_name")
    if model:
        parts.append(c(MAGENTA, model))

    effort = data.get("effort", {}).get("level")
    if effort:
        parts.append(c(BLUE, f"think:{effort}"))
    elif data.get("thinking", {}).get("enabled"):
        parts.append(c(BLUE, "think"))

    rev = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir", "--git-dir", "--show-toplevel")
    common, git_dir, top = (rev.splitlines() + ["", "", ""])[:3]
    parts.append(dir_part(cwd, common, git_dir, top))

    branch = git(cwd, "branch", "--show-current")
    if branch:
        # Pure marks a branch with uncommitted changes to tracked files with `*`.
        dirty = "*" if git(cwd, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no") else ""
        parts.append(c(GREEN, f"⎇ {branch}{dirty}"))

    if "--no-prs" not in sys.argv:
        with contextlib.suppress(Exception):
            parts.extend(pr_parts(data, cwd, common, branch))

    ctx = data.get("context_window") or {}
    size = ctx.get("context_window_size")
    if size:
        used = ctx.get("total_input_tokens") or 0
        pct = ctx.get("used_percentage")
        pct = used / size * 100 if pct is None else pct
        ac = " AC" if auto_compact_on() else ""
        parts.append(c(DIM, f"▥ {tokens(used)}/{tokens(size)} ({pct:.1f}%){ac}"))

    if data.get("rate_limits"):
        parts.append(c(WHITE, "(sub)"))
    else:
        cost = data.get("cost", {}).get("total_cost_usd")
        if cost is not None:
            parts.append(c(WHITE, f"${cost:.2f}"))

    print(sep.join(parts))


if __name__ == "__main__":
    main()
