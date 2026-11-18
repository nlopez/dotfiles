#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/claude/hooks/executable_track-prs.py
# Remember the PRs this session opens or pushes to, for the status line's
# session PR list.
#   PostToolUse (Bash):
#     gh pr create|ready|edit|merge -> PR URLs printed in the command output
#     git push                      -> the pushed branch's PR, looked up in the background
#   SessionStart (resume):
#     the same rules applied to the transcript's Bash calls, in the background,
#     so PRs from before the hook ran or from a forked parent session are found
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pr_tracking  # noqa: E402

try:
    data = json.load(sys.stdin)
    session_id = data.get("session_id") or ""
    cwd = data.get("cwd") or os.getcwd()
    if not session_id:
        sys.exit(0)
    if data.get("hook_event_name") == "SessionStart":
        transcript = data.get("transcript_path") or ""
        if os.path.isfile(transcript):
            subprocess.Popen(
                [sys.executable, pr_tracking.__file__, "backfill", session_id, transcript],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    response = data.get("tool_response")
    output = json.dumps(response) if not isinstance(response, str) else response
    for url in pr_tracking.command_prs(command, output):
        pr_tracking.record(session_id, url)
    if pr_tracking.PUSH_COMMAND.search(command):
        pr_tracking.spawn_resolve(session_id, cwd)
except Exception:
    pass
