#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/claude/executable_statusline.py
# Claude Code status line modelled on pi's powerline footer:
#   model | think:<effort> | dir <name> | ⎇ <branch> | PR #12 ✓ approved | PRs #9 ✗ · repo#4 merged
#   | ▥ used/size (pct%) AC | (sub) | 🧠 <project> · ready · ● ADHD ON
# PR data comes from pr_tracking.py (cached `gh pr view`, refreshed in the background).
# Claude pipes a JSON blob on stdin; whatever we print is the status line.
import contextlib
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_tracking  # noqa: E402

RESET = "\033[0m"


# Basic ANSI SGR codes (30-37 / 90-97) so colours follow the terminal theme.
MAGENTA, BLUE, CYAN, GREEN, YELLOW, RED, WHITE, DIM = 35, 34, 36, 32, 33, 31, 37, 90


def c(code, text):
    return f"\033[{code}m{text}{RESET}"


def tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".removesuffix(".0") + "M"
    if n >= 1000:
        return f"{n / 1000:.1f}".removesuffix(".0") + "k"
    return str(n)


def git(cwd, *args):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            timeout=1,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def engram_ready():
    try:
        with urllib.request.urlopen("http://127.0.0.1:7437/health", timeout=0.3) as r:
            return r.status == 200
    except Exception:
        return False


CHECK_GLYPH = {"pass": (GREEN, "✓"), "fail": (RED, "✗"), "pending": (YELLOW, "…")}
REVIEW = {"APPROVED": (GREEN, "approved"), "CHANGES_REQUESTED": (RED, "changes")}


def pr_label(pr, prefix=""):
    """'#12 draft ✓ approved'-style label; state and review only when notable."""
    bits = [c(GREEN, f"{prefix}#{pr.get('number')}")]
    state = pr.get("state")
    if state == "MERGED":
        bits.append(c(MAGENTA, "merged"))
    elif state == "CLOSED":
        bits.append(c(RED, "closed"))
    else:
        if pr.get("isDraft"):
            bits.append(c(DIM, "draft"))
        glyph = CHECK_GLYPH.get(pr_tracking.checks(pr))
        if glyph:
            bits.append(c(*glyph))
        review = REVIEW.get(pr.get("reviewDecision"))
        if review:
            bits.append(c(*review))
    return " ".join(bits)


def pr_parts(data, cwd, common, branch):
    parts = []
    current = None
    if common and branch and branch not in ("main", "master"):
        current = pr_tracking.branch_pr(cwd, common, branch)
        if current:
            parts.append(f"{c(WHITE, 'PR')} {pr_label(current)}")
    here = os.path.basename(os.path.dirname(common)) if common else ""
    others = [u for u in pr_tracking.session_prs(data.get("session_id")) if u != (current or {}).get("url")]
    labels = []
    for url in others[-3:]:
        pr = pr_tracking.url_pr(url) or {"number": url.rsplit("/", 1)[-1]}
        repo = pr_tracking.repo_of(url)
        labels.append(pr_label(pr, "" if repo == here else repo))
    if labels:
        more = c(DIM, f" +{len(others) - 3}") if len(others) > 3 else ""
        parts.append(f"{c(WHITE, 'PRs')} " + c(DIM, " · ").join(labels) + more)
    return parts


def auto_compact_on(config_dir):
    try:
        with open(os.path.join(config_dir, ".claude.json")) as f:
            return json.load(f).get("autoCompactEnabled", True)
    except Exception:
        return True


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    cwd = data.get("workspace", {}).get("current_dir") or data.get("cwd") or os.getcwd()
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.config/claude")
    sep = c(DIM, " | ")
    parts = []

    model = data.get("model", {}).get("display_name")
    if model:
        parts.append(c(MAGENTA, model))

    effort = data.get("effort", {}).get("level")
    if effort:
        parts.append(c(BLUE, f"think:{effort}"))
    elif data.get("thinking", {}).get("enabled"):
        parts.append(c(BLUE, "think"))

    parts.append(c(CYAN, f"dir {os.path.basename(cwd.rstrip('/')) or '/'}"))

    branch = git(cwd, "branch", "--show-current")
    if branch:
        parts.append(c(GREEN, f"⎇ {branch}"))

    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    with contextlib.suppress(Exception):
        parts.extend(pr_parts(data, cwd, common, branch))

    ctx = data.get("context_window") or {}
    size = ctx.get("context_window_size")
    if size:
        used = ctx.get("total_input_tokens") or 0
        pct = ctx.get("used_percentage")
        pct = used / size * 100 if pct is None else pct
        ac = " AC" if auto_compact_on(config_dir) else ""
        parts.append(c(DIM, f"▥ {tokens(used)}/{tokens(size)} ({pct:.1f}%){ac}"))

    if data.get("rate_limits"):
        parts.append(c(WHITE, "(sub)"))
    else:
        cost = data.get("cost", {}).get("total_cost_usd")
        if cost is not None:
            parts.append(c(WHITE, f"${cost:.2f}"))

    # Engram: project = repo name (worktree-safe via the common git dir), health = local server.
    project = os.path.basename(os.path.dirname(common)) if common else ""
    if project:
        state = c(YELLOW, "ready") if engram_ready() else c(RED, "offline")
        parts.append(f"🧠 {c(YELLOW, project)} {c(DIM, '·')} {state}")

    adhd = ""
    if os.path.exists(os.path.join(config_dir, ".i-have-adhd-always")):
        adhd = f" {c(DIM, '·')} {c(GREEN, '●')} {c(MAGENTA, 'ADHD ON')}"

    print(sep.join(parts) + adhd)


if __name__ == "__main__":
    main()
