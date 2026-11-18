#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/claude/hooks/executable_track-prs.py
# PostToolUse (Bash): remember the PRs this session opens or pushes to, for the
# status line's session PR list.
#   gh pr create|ready|edit|merge -> PR URLs printed in the command output
#   git push                      -> the pushed branch's PR, looked up in the background
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pr_tracking  # noqa: E402

try:
    data = json.load(sys.stdin)
    session_id = data.get("session_id") or ""
    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    response = data.get("tool_response")
    output = json.dumps(response) if not isinstance(response, str) else response
    if session_id and re.search(r"\bgh\s+pr\s+(create|ready|edit|merge)\b", command):
        for url in dict.fromkeys(pr_tracking.PR_URL.findall(output)):
            pr_tracking.record(session_id, url)
    if session_id and re.search(r"\bgit\b[^;&|]*\bpush\b", command):
        subprocess.Popen(
            [sys.executable, pr_tracking.__file__, "resolve", session_id, cwd],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
except Exception:
    pass
