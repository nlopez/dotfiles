#!/usr/bin/env python3
"""
Consolidated Claude Code hook dispatcher.

Dispatches based on hook_event_name (and tool_name for PreToolUse) in the
JSON payload received on stdin.

PreToolUse[Bash]:
  bash_permission   auto-allow safe commands; let Claude decide on the rest
  gh_pr_draft       inject --draft into `gh pr create`
  gh_attribution    append co-authorship footer to:
                      gh {pr,issue} {create,edit,comment,review} --body / --body-file
                      gh api .../pulls/<n>/comments/<n>/replies  -f/-F body=...

Notification[idle_prompt|permission_prompt]:
  set tmux @pi-status → 🛎️

Stop:
  set tmux @pi-status → ✳️ or 🛎️  + terminal-notifier notification

SessionEnd:
  clear tmux @pi-status

UserPromptSubmit / PostToolUse:
  set tmux @pi-status → 🤖

Known limitations (gh attribution):
  - --body-file - (stdin) cannot be intercepted
  - $'...' ANSI-C quoting in --body is not intercepted
  - gh api --input <file> body is not intercepted
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── gh attribution ────────────────────────────────────────────────────────────

_ATTRIBUTION_FOOTER = "\n\n---\n*Co-authored with Claude*"
_ATTRIBUTION_MARKER = "Co-authored with Claude"

# gh {pr,issue} {create,edit,comment,review}
_GH_CONTENT_RE = re.compile(r"\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b")

# gh api PR review-comment reply endpoint
# e.g. gh api repos/owner/repo/pulls/123/comments/456/replies
_GH_API_REPLY_RE = re.compile(
    r"\bgh\s+api\b.*?/pulls/\d+/comments/\d+/replies\b",
    re.DOTALL,
)

# --body-file <path> or -F <path> (quoted or unquoted, not stdin "-")
_BODY_FILE_RE = re.compile(r"(?:--body-file|-F)\s+(?:\"([^\"]+)\"|'([^']+)'|(?!-)(\S+))")

# --body "..." or --body '...' after a gh content subcommand
_BODY_INLINE_RE = re.compile(
    r"(\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b[\s\S]*?)"
    r"--body\s+(\"((?:[^\"\\]|\\[\s\S])*)\"|'((?:[^'\\]|\\[\s\S])*)')",
    re.DOTALL,
)

# -f body=... / -F body=... / --field body=... / --raw-field body=...
_API_BODY_FIELD_RE = re.compile(
    r"((?:-[fF]|--(?:field|raw-field))\s+body=)"
    r"(\"((?:[^\"\\]|\\[\s\S])*)\"|'((?:[^'\\]|\\[\s\S])*)'|(\S+))"
)


def _inject_inline_body(cmd: str) -> str | None:
    """Rewrite --body value in the command string. Returns new cmd or None."""
    if "--body" not in cmd or _ATTRIBUTION_MARKER in cmd:
        return None
    modified = False

    def _replace(m: re.Match) -> str:
        nonlocal modified
        modified = True
        prefix = m.group(1)
        body = m.group(3) if m.group(3) is not None else (m.group(4) or "")
        safe = body.replace('"', '\\"')
        return f'{prefix}--body "{safe}{_ATTRIBUTION_FOOTER}"'

    result = _BODY_INLINE_RE.sub(_replace, cmd)
    return result if modified else None


def _inject_body_file(cmd: str) -> bool:
    """Append footer to a --body-file target on disk. Returns True if patched."""
    m = _BODY_FILE_RE.search(cmd)
    if not m:
        return False
    raw_path = m.group(1) or m.group(2) or m.group(3)
    if not raw_path or raw_path == "-":
        return False
    try:
        p = Path(raw_path)
        content = p.read_text()
    except OSError:
        return False
    if _ATTRIBUTION_MARKER in content:
        return False
    p.write_text(content + _ATTRIBUTION_FOOTER)
    return True


def _inject_api_reply_body(cmd: str) -> str | None:
    """Rewrite -f body=... in a gh api reply call. Returns new cmd or None."""
    if _ATTRIBUTION_MARKER in cmd:
        return None
    modified = False

    def _replace(m: re.Match) -> str:
        nonlocal modified
        modified = True
        flag_prefix = m.group(1)
        if m.group(3) is not None:
            body = m.group(3)
        elif m.group(4) is not None:
            body = m.group(4)
        else:
            body = m.group(5) or ""
        safe = body.replace('"', '\\"')
        return f'{flag_prefix}"{safe}{_ATTRIBUTION_FOOTER}"'

    result = _API_BODY_FIELD_RE.sub(_replace, cmd)
    return result if modified else None


def _apply_gh_attribution(cmd: str) -> str | None:
    """
    Inject the attribution footer into a gh command. Returns the rewritten
    command string, or None if no inline rewrite occurred (a --body-file may
    still have been patched on disk as a side-effect).
    """
    if _GH_CONTENT_RE.search(cmd):
        new_cmd = _inject_inline_body(cmd)
        if new_cmd is not None:
            return new_cmd
        _inject_body_file(cmd)  # side-effect only
        return None

    if _GH_API_REPLY_RE.search(cmd):
        return _inject_api_reply_body(cmd)

    return None


# ── gh pr draft ───────────────────────────────────────────────────────────────

_GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")


def _apply_gh_pr_draft(cmd: str) -> str | None:
    """Inject --draft into `gh pr create` if not already present."""
    if _GH_PR_CREATE_RE.search(cmd) and "--draft" not in cmd:
        return _GH_PR_CREATE_RE.sub("gh pr create --draft", cmd, count=1)
    return None


# ── bash permission ───────────────────────────────────────────────────────────
# Mirrors the logic in the former bash-regex-permission.sh:
#   deny patterns → no decision (Claude handles it)
#   allow patterns → emit permissionDecision=allow
# Deny is checked first so a command matching both lists is never auto-allowed.

_DENY_RES: list[re.Pattern[str]] = [
    re.compile(r"(?:find|fdfind)\b.*--exec(?:-batch)?\b"),
    re.compile(r"\bgit\b.*?\s--force(?:-with-lease)?\b"),
    re.compile(r"\bgit\b.*?\sreset\s+--hard\b"),
    re.compile(r"\bgit\b.*?\sclean\b.*?(?:-[^\s-]*f\b|--force\b)"),
    re.compile(r"\bgit\b.*?\sbranch\b.*?\s-D\b"),
    re.compile(r"\bgh\b.*?\spr\s+close\b"),
    re.compile(r"\brm\s+-rf\s+[/~]"),
    re.compile(r"\bchmod\s+777\b"),
]

_ALLOW_RES: list[re.Pattern[str]] = [
    # kubectl read-only
    re.compile(
        r"^\s*kubectl\s+(?:get|describe|logs|top|explain|version|cluster-info|api-resources|api-versions|diff)\b"
    ),
    # git (read-only + allowed writes)
    re.compile(
        r"^\s*git\s+(?:status|log|diff|show|branch|blame|tag|stash|fetch|pull|checkout|switch|rebase|merge|cherry-pick|revert|add|restore|rm|mv|remote|config|rev-parse|ls-files|ls-tree|shortlog|reflog|describe|name-rev|for-each-ref|worktree)\b"
    ),
    # gh (approved subcommands)
    re.compile(
        r"^\s*gh\s+(?:pr\s+(?:create|edit|merge|view|list|checkout|diff|checks|ready|review|comment)|issue|repo|run|workflow|auth|status)\b"
    ),
    # file inspection
    re.compile(r"^\s*(?:cat|head|tail|wc|file|stat|ls|tree)\b"),
    # text search
    re.compile(r"^\s*(?:grep|rg)\b"),
    # find with --name filter
    re.compile(r"^\s*find\b.*\b--name\b"),
    # fd/fdfind (deny list catches --exec first)
    re.compile(r"^\s*(?:fd|fdfind)\b"),
    # help / version / dry-run flags (anywhere in command)
    re.compile(r"--(?:help|version|dry-run)\b"),
    re.compile(r"\s-h\b"),
    # go
    re.compile(r"^\s*go\s+(?:list|vet|build|fmt|test|run|mod)\b"),
    # system info
    re.compile(
        r"^\s*(?:pwd|date|uname|hostname|whoami|id|uptime|which|whereis|type|env|printenv|ps|pgrep|df|du|lsof)\b"
    ),
    # text processing
    re.compile(r"^\s*(?:diff|delta|colordiff|sort|uniq|cut|tr|awk|sed|jq|yq|bat|less|more)\b"),
    # brew read-only
    re.compile(r"^\s*brew\s+(?:list|info|search|outdated|leaves|deps|desc|uses)\b"),
    # npm / yarn / pnpm read-only
    re.compile(r"^\s*npm\s+(?:list|info|outdated|ls|why|audit)\b"),
    re.compile(r"^\s*(?:yarn|pnpm)\s+(?:list|info|outdated|ls|why|audit)\b"),
    # pip read-only
    re.compile(r"^\s*pip[0-9]?\s+(?:list|show|freeze|check)\b"),
    # poetry / pipenv read-only
    re.compile(r"^\s*(?:pipenv|poetry)\s+(?:graph|show|info|tree|check)\b"),
    # cargo read-only
    re.compile(r"^\s*cargo\s+(?:check|clippy|doc|metadata|pkgid|locate-project|tree|verify-project)\b"),
    # chezmoi read-only
    re.compile(r"^\s*chezmoi\s+(?:diff|status|data|cat|managed|unmanaged|doctor|dump|execute-template)\b"),
    # docker read-only
    re.compile(r"^\s*docker\s+(?:ps|images|inspect|logs|stats|top|info|version)\b"),
    re.compile(r"^\s*docker\s+(?:network|volume|container)\s+ls\b"),
    # curl/wget inspection
    re.compile(r"^\s*curl\s+(?:-I|--head)\b"),
    re.compile(r"^\s*wget\s+(?:--server-response|--spider)\b"),
    # macOS system tools
    re.compile(r"^\s*(?:sw_vers|system_profiler|diskutil\s+list)\b"),
    re.compile(r"^\s*(?:xcode-select|xcrun)\b"),
]


def _bash_permission(cmd: str) -> dict | None:
    """Return allow decision for safe commands; None for everything else."""
    if any(rx.search(cmd) for rx in _DENY_RES):
        return None
    if any(rx.search(cmd) for rx in _ALLOW_RES):
        return {
            "permissionDecision": "allow",
            "permissionDecisionReason": "Matches allow pattern",
        }
    return None


# ── PreToolUse[Bash] dispatcher ───────────────────────────────────────────────


def _on_pre_tool_use_bash(data: dict) -> None:
    cmd: str = data.get("tool_input", {}).get("command", "")
    if not cmd:
        return

    hook_extras: dict = {}

    # 1. Permission — auto-allow safe commands
    perm = _bash_permission(cmd)
    if perm:
        hook_extras.update(perm)

    # 2. gh pr draft — inject --draft (updates cmd for downstream steps)
    new_cmd = _apply_gh_pr_draft(cmd)
    if new_cmd is not None:
        cmd = new_cmd
        hook_extras.setdefault("updatedInput", {})["command"] = cmd

    # 3. gh attribution — uses the possibly-updated cmd from step 2
    attr_cmd = _apply_gh_attribution(cmd)
    if attr_cmd is not None:
        hook_extras.setdefault("updatedInput", {})["command"] = attr_cmd

    if hook_extras:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        **hook_extras,
                    }
                }
            )
        )


# ── tmux helpers ──────────────────────────────────────────────────────────────


def _tmux_set(pane: str, value: str) -> None:
    subprocess.run(
        ["tmux", "set-option", "-w", "-t", pane, "@pi-status", value],
        capture_output=True,
    )


def _tmux_unset(pane: str) -> None:
    subprocess.run(
        ["tmux", "set-option", "-wu", "-t", pane, "@pi-status"],
        capture_output=True,
    )


def _detect_terminal_bundle() -> str:
    cache_path = "/tmp/claude_terminal_bundle"
    with contextlib.suppress(OSError):
        if os.path.isfile(cache_path):
            return Path(cache_path).read_text().strip()
    candidates = {
        "iTerm2": "com.googlecode.iterm2",
        "ghostty": "com.mitchellh.ghostty",
        "kitty": "net.kovidgoyal.kitty",
        "WezTerm": "com.github.wez.wezterm",
        "Terminal": "com.apple.Terminal",
    }
    bundle = "com.apple.Terminal"
    for app, bid in candidates.items():
        if subprocess.run(["pgrep", "-xi", app], capture_output=True).returncode == 0:
            bundle = bid
            break
    with contextlib.suppress(OSError):
        Path(cache_path).write_text(bundle)
    return bundle


def _terminal_notify(message: str, pane: str) -> None:
    if not shutil.which("terminal-notifier"):
        return
    bundle = _detect_terminal_bundle()
    info = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane, "#{session_name} #{window_index} #{window_name}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    parts = info.split(" ", 2)
    session = parts[0] if parts else ""
    window_index = parts[1] if len(parts) > 1 else ""
    window_name = parts[2] if len(parts) > 2 else ""
    tmux_bin = shutil.which("tmux") or "tmux"
    click_cmd = f"'{tmux_bin}' switch-client -t '{session}:{window_index}' 2>/dev/null; open -b '{bundle}'"
    subprocess.run(
        [
            "terminal-notifier",
            "-title",
            "Claude",
            "-subtitle",
            window_name,
            "-message",
            message,
            "-activate",
            bundle,
            "-execute",
            click_cmd,
            "-sound",
            "Glass",
            "-group",
            f"claude-{pane}",
        ],
        capture_output=True,
    )


# ── event handlers ────────────────────────────────────────────────────────────


def _on_stop(data: dict, pane: str) -> None:
    last_msg: str = data.get("last_assistant_message", "")
    last_char = last_msg.rstrip()[-1:] if last_msg.rstrip() else ""
    emoji = "🛎️" if last_char == "?" else "✳️"
    _tmux_set(pane, f"{emoji} ")
    if emoji == "✳️":
        _terminal_notify("Complete", pane)


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    event: str = data.get("hook_event_name", "")

    # PreToolUse needs no tmux; dispatch on tool_name
    if event == "PreToolUse":
        if data.get("tool_name") == "Bash":
            _on_pre_tool_use_bash(data)
        return

    # All remaining handlers require an active tmux pane
    if not os.environ.get("TMUX"):
        return
    pane = os.environ.get("TMUX_PANE", "")
    if not pane:
        return

    if event == "Notification":
        _tmux_set(pane, "🛎️ ")
    elif event == "Stop":
        _on_stop(data, pane)
    elif event == "SessionEnd":
        _tmux_unset(pane)
    elif event in ("UserPromptSubmit", "PostToolUse"):
        _tmux_set(pane, "🤖 ")


if __name__ == "__main__":
    main()
