#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_claude/hooks/executable_track-prs.py
# Claude Code adapter for the shared session PR box (~/.config/argus-pr/argus_pr.py).
#   PostToolUse (Bash):
#     gh pr create|ready|edit|merge -> PR URLs printed in the command output
#     git push                      -> the pushed branch's PR, looked up in the background
#   SessionStart:
#     in Rex, open the tiled PR pane beside this pane or point it at this session,
#     and tell Claude the session ID and the argus_pr.py status command
#   SessionStart (resume):
#     the same rules applied to the transcript's Bash calls, in the background,
#     so PRs from before the hook ran or from a forked parent session are found
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.expanduser("~/.config/argus-pr"))
import argus_pr  # noqa: E402
import pr_float  # noqa: E402
import pr_tracking  # noqa: E402

try:
    data = json.load(sys.stdin)
    session_id = data.get("session_id") or ""
    cwd = data.get("cwd") or os.getcwd()
    if not session_id:
        sys.exit(0)
    if data.get("hook_event_name") == "SessionStart":
        source = data.get("source") or ""
        if source in ("startup", "clear"):
            block = os.environ.get("REX_BLOCK")
            prev_sid = pr_float._state(block).get("session_id") if block else ""
            if prev_sid and prev_sid != session_id:
                pr_tracking.reset_session(prev_sid)
            pr_tracking.reset_session(session_id)
        argus_pr.attach(session_id, cwd, pr_float.ancestor_pid("claude") or "")
        transcript = data.get("transcript_path") or ""
        if source == "resume" and os.path.isfile(transcript):
            subprocess.Popen(
                [sys.executable, pr_tracking.__file__, "backfill", session_id, transcript],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        box = "python3 ~/.config/argus-pr/argus_pr.py"
        context = (
            f"Argus PR: this session's ID is {session_id}. `{box} status {session_id}` lists the PRs it"
            " tracks, one line each with state, head commit, checks, failing checks and review."
            f" `{box} add {session_id} <url>` tracks another PR."
        )
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    response = data.get("tool_response")
    output = json.dumps(response) if not isinstance(response, str) else response
    argus_pr.record_command(session_id, cwd, command, output)
except Exception:
    pass
