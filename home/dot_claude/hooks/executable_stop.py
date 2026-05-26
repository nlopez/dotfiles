#!/usr/bin/env python3
"""Sets ✳️ when Claude is done, 🛎️ when the last message ends with a question.
Hooked on the Stop event.

Sends a macOS terminal-notifier notification for the ✳️ (complete) case.
The 🛎️ (attention) notification is handled by the Notification[idle_prompt]
hook so it fires reliably for all attention states, not just question endings.
"""

import contextlib
import json
import os
import shutil
import subprocess
import sys


def _detect_bundle() -> str:
    cache = "/tmp/claude_terminal_bundle"
    try:
        if os.path.isfile(cache):
            return open(cache).read().strip()
    except OSError:
        pass
    apps = {
        "iTerm2": "com.googlecode.iterm2",
        "ghostty": "com.mitchellh.ghostty",
        "kitty": "net.kovidgoyal.kitty",
        "WezTerm": "com.github.wez.wezterm",
        "Terminal": "com.apple.Terminal",
    }
    bundle = "com.apple.Terminal"
    for app, bid in apps.items():
        if subprocess.run(["pgrep", "-xi", app], capture_output=True).returncode == 0:
            bundle = bid
            break
    with contextlib.suppress(OSError), open(cache, "w") as f:
        f.write(bundle)
    return bundle


def _notify(msg: str, pane: str) -> None:
    if not shutil.which("terminal-notifier"):
        return
    bundle = _detect_bundle()
    info = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane, "#{session_name} #{window_index} #{window_name}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    parts = info.split(" ", 2)
    session = parts[0] if len(parts) > 0 else ""
    window_index = parts[1] if len(parts) > 1 else ""
    window_name = parts[2] if len(parts) > 2 else ""
    tmux_bin = shutil.which("tmux") or "tmux"
    click = f"'{tmux_bin}' switch-client -t '{session}:{window_index}' 2>/dev/null; open -b '{bundle}'"
    subprocess.run(
        [
            "terminal-notifier",
            "-title",
            "Claude",
            "-subtitle",
            window_name,
            "-message",
            msg,
            "-activate",
            bundle,
            "-execute",
            click,
            "-sound",
            "Glass",
            "-group",
            f"claude-{pane}",
        ],
        capture_output=True,
    )


if not os.environ.get("TMUX"):
    sys.exit(0)

pane = os.environ.get("TMUX_PANE", "")
if not pane:
    sys.exit(0)

data = json.load(sys.stdin)
last_msg = data.get("last_assistant_message", "")
last_char = last_msg.rstrip()[-1:] if last_msg.rstrip() else ""

emoji = "🛎️" if last_char == "?" else "✳️"

subprocess.run(
    ["tmux", "set-option", "-w", "-t", pane, "@pi-status", f"{emoji} "],
    capture_output=True,
)

if emoji == "✳️":
    _notify("Complete", pane)
