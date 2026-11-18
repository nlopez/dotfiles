#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/pr-box/pr_box.py
"""
Agent-neutral entry point for the session PR box. Each coding agent has a thin
adapter that reports its session and the PRs it opens; the tracking and the Rex
floating box (pr_tracking.py, pr_float.py) are the same for all of them.

  attach <session_id> <cwd> [agent_pid]  open the box for this Rex pane, or
                                         point it at this session. With an
                                         agent_pid the box closes when it exits.
  record <session_id> <cwd>              stdin: {"command": ..., "output": ...}.
                                         Track the PRs a shell command printed
                                         and, after a git push, the branch's PR.
  add <session_id> <url>                 track one PR
  set <session_id> [url...]              replace the session's PR list
  reopen                                 reopen a closed box for this pane
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_float  # noqa: E402
import pr_tracking  # noqa: E402


def _detached(*args):
    subprocess.Popen(
        [sys.executable, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def attach(session_id, cwd, agent_pid=""):
    _detached(pr_float.__file__, "ensure", session_id, cwd, str(agent_pid or ""))


def record_command(session_id, cwd, command, output):
    for url in pr_tracking.command_prs(command, output):
        pr_tracking.record(session_id, url)
    if pr_tracking.PUSH_COMMAND.search(command):
        pr_tracking.spawn_resolve(session_id, cwd)
    if pr_tracking.PUSH_COMMAND.search(command) or pr_tracking.PR_COMMAND.search(command):
        pr_tracking.invalidate()


def main(argv):
    cmd, args = (argv[:1] or [""])[0], argv[1:]
    if cmd == "attach" and len(args) >= 2:
        attach(*args[:3])
    elif cmd == "record" and len(args) == 2:
        data = json.load(sys.stdin)
        record_command(args[0], args[1], data.get("command") or "", data.get("output") or "")
    elif cmd == "add" and len(args) == 2:
        pr_tracking.record(*args)
    elif cmd == "set" and args:
        pr_tracking.set_session(args[0], args[1:])
    elif cmd == "reopen":
        pr_float.reopen()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
