#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/claude/hooks/executable_pr-notify.py
# Claude Code delivery of the PR box's notifications (CI failed, approved, changes requested),
# which pr_float.py queues per session while the box is open.
#   Stop (asyncRewake): wait in the background for a queued notification, then
#     print it to stderr and exit 2, which wakes Claude to handle it even when
#     the session is idle. Each Stop starts a new waiter; older ones step aside.
#   UserPromptSubmit: hand queued notifications to Claude with the prompt.
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.config/pr-box"))
import pr_float  # noqa: E402
import pr_tracking  # noqa: E402

# Just under the Stop hook's timeout in settings, so the waiter ends on its own.
LIFETIME = 6 * 3600 - 60
TICK = 3


def wait(session_id):
    owner = pr_tracking._session_path(session_id, "wake", ".pid")
    os.makedirs(os.path.dirname(owner), exist_ok=True)
    with open(owner, "w") as f:
        f.write(str(os.getpid()))
    agent = pr_float.ancestor_pid("claude")
    deadline = time.time() + LIFETIME
    while time.time() < deadline:
        try:
            with open(owner) as f:
                if f.read().strip() != str(os.getpid()):
                    return 0
        except OSError:
            return 0
        if agent and not pr_float._alive(agent):
            return 0
        message = pr_tracking.drain(session_id)
        if message:
            sys.stderr.write(message + "\n")
            return 2
        time.sleep(TICK)
    return 0


def main():
    data = json.load(sys.stdin)
    session_id = data.get("session_id") or ""
    if not session_id or not os.environ.get("REX_SESSION"):
        return 0
    event = data.get("hook_event_name")
    if event == "Stop":
        return wait(session_id)
    if event == "UserPromptSubmit":
        message = pr_tracking.drain(session_id)
        if message:
            output = {"hookEventName": "UserPromptSubmit", "additionalContext": message}
            print(json.dumps({"hookSpecificOutput": output}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
