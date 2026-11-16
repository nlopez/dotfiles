#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/claude/executable_statusline.py
# Claude Code status line modelled on pi's powerline footer:
#   model | think:<effort> | dir <name> | ⎇ <branch> | ▥ used/size (pct%) AC | (sub) | 🧠 <project> · ready · ● ADHD ON
# Claude pipes a JSON blob on stdin; whatever we print is the status line.
import json
import os
import subprocess
import sys
import urllib.request

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
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
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
