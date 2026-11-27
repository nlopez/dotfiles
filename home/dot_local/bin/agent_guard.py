"""Shared parts of the agent-*-guard hooks: hook I/O and commit message stripping.

Each guard reads the hook JSON on stdin ({"tool_input": {"command": ...}}) and
exits 2 with its reason on stderr to block, 0 to allow.
"""

import json
import re
import sys

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?\n\2\b", re.S)
# Quoted values only: an unquoted word after -t or -b may be a command (`xargs -t rm`).
MESSAGE_ARG = re.compile(
    r"""(?:\s(?:-m|-b|-t|--message|--body|--title)(?:=|\s+))"""
    r"""(?:"(?:[^"\\]|\\.)*"|'[^']*'|\$'(?:[^'\\]|\\.)*')"""
)


def strip_messages(command: str) -> str:
    """The command without heredoc bodies and quoted commit/PR message arguments."""
    return MESSAGE_ARG.sub(" ", HEREDOC.sub(" ", command))


def run(blocked, reason: str) -> None:
    try:
        command = json.load(sys.stdin).get("tool_input", {}).get("command") or ""
    except (ValueError, AttributeError):
        sys.exit(0)
    if blocked(strip_messages(command)):
        print(reason, file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
