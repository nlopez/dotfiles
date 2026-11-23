#!/usr/bin/env python3
# Managed by chezmoi — source: home/dot_config/argus-pr/argus_pr.py
"""
Agent-neutral entry point for the session PR box. Each coding agent has a thin
adapter that reports its session and the PRs it opens; the tracking and the Rex
tiled pane (pr_tracking.py, pr_float.py) are the same for all of them.

  attach <session_id> <cwd> [agent_pid]  open the box for this Rex pane, or
                                         point it at this session. With an
                                         agent_pid the box closes when it exits.
  record <session_id> <cwd>              stdin: {"command": ..., "output": ...}.
                                         Track the PRs a shell command printed
                                         and, after a git push, the branch's PR.
  add <session_id> <url>                 track one PR
  set <session_id> [url...]              replace the session's PR list
  reset <session_id>                     clear a session's PRs, baselines and inbox
  reopen                                 reopen the agent's box: in this pane,
                                         or in the pane of the session it was
                                         resumed or forked from
  status <session_id>                    print one line per tracked PR: state,
                                         head commit, checks, failing checks and
                                         review, from the cached status
  drain <session_id> [consumer]          print unread PR notifications and
                                         advance the consumer's cursor
  events <session_id> [n]                print the last n (default 20) PR
                                         events for a session (read-only)
  log [n]                                print the last n (default 50) watches
                                         and events across all sessions
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
        pr_tracking.note_push(session_id)
        pr_tracking.spawn_resolve(session_id, pr_tracking.push_dir(command, cwd))
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
    elif cmd == "reset" and len(args) == 1:
        pr_tracking.reset_session(args[0])
    elif cmd == "reopen":
        pr_float.reopen(pr_tracking.agent_session_ids())
    elif cmd == "status" and len(args) == 1:
        print(pr_tracking.status_lines(args[0]))
    elif cmd == "drain" and 1 <= len(args) <= 2:
        print(pr_tracking.drain(*args))
    elif cmd == "events" and 1 <= len(args) <= 2 and (len(args) == 1 or args[1].isdigit()):
        print(pr_tracking.session_events(args[0], int(args[1]) if len(args) == 2 else 20))
    elif cmd == "log" and len(args) <= 1 and all(a.isdigit() for a in args):
        print(pr_tracking.read_log(int(args[0]) if args else 50))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
