#!/usr/bin/env python3
"""Run each agent guard hook on sample commands and check which ones it blocks."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent / "home"
RM = HOME / "dot_local/bin/executable_agent-rm-guard"
STAGE = HOME / "dot_local/bin/executable_agent-stage-guard"
BYPASS = HOME / "dot_local/bin/executable_agent-bypass-guard"
WORKTREE = HOME / "dot_local/bin/executable_agent-worktree-guard"

# (guard, command, blocked)
CASES = [
    (RM, "rm -rf build", True),
    (RM, "echo hi && rm x", True),
    (RM, "ls | xargs rm", True),
    (RM, "ls | xargs -t rm", True),
    (RM, "command rm x", True),
    (RM, "/bin/rm x", True),
    (RM, "sudo rm x", True),
    (RM, "sudo -u bob rm x", True),
    (RM, "sudo -E rm x", True),
    (RM, "find . -name '*.pyc' -delete", True),
    (RM, "find . -name x -exec rm {} +", True),
    (RM, "git rm x", False),
    (RM, "trash x", False),
    (RM, "git commit -m fixrm", False),
    (RM, 'gh pr create --body "use rm -rf"', False),
    (RM, "git commit -F - <<EOF\nrm stuff\nEOF", False),
    (STAGE, "git add -A", True),
    (STAGE, "git add --all", True),
    (STAGE, "git add -u", True),
    (STAGE, "git add .", True),
    (STAGE, "git add -- .", True),
    (STAGE, "git add :/", True),
    (STAGE, "git -C /x add .", True),
    (STAGE, 'git commit -am "x"', True),
    (STAGE, "git commit -m x --all", True),
    (STAGE, "git add src/a.py", False),
    (STAGE, 'git commit -m "add -A"', False),
    (STAGE, "git commit -m x", False),
    (BYPASS, "git commit --no-verify -m x", True),
    (BYPASS, "git commit -n -m x", True),
    (BYPASS, "git push --no-verify", True),
    (BYPASS, "git commit --no-gpg-sign -m x", True),
    (BYPASS, "git -c commit.gpgsign=false commit -m x", True),
    (BYPASS, "git config commit.gpgsign false", True),
    (BYPASS, "git config --unset commit.gpgsign", True),
    (BYPASS, "git -c core.hooksPath=/dev/null commit -m x", True),
    (BYPASS, "git -c hook.require-signed-commit.enabled=false commit -m x", True),
    (BYPASS, "GIT_CONFIG_COUNT=1 git commit -m x", True),
    (BYPASS, "git fcommit -m x", True),
    (BYPASS, 'git commit -m "skip --no-verify"', False),
    (BYPASS, "git commit -m x --amend --no-edit", False),
    (BYPASS, "git commit --signoff -m x", False),
    (BYPASS, "git commit -S -m x", False),
    (BYPASS, "git commit -m x -- some-file", False),
    (BYPASS, "git commit -m msg && echo done -n", False),
]


def run(guard, payload):
    result = subprocess.run([sys.executable, str(guard)], input=json.dumps(payload), capture_output=True, text=True)
    return result.returncode == 2


def main():
    failures = []
    for guard, command, want in CASES:
        if run(guard, {"tool_name": "Bash", "tool_input": {"command": command}}) != want:
            failures.append(f"{guard.name}: {command!r} should be {'blocked' if want else 'allowed'}")

    with tempfile.TemporaryDirectory() as tmp:
        main_repo, linked, plain = Path(tmp, "main"), Path(tmp, "linked"), Path(tmp, "plain")
        (main_repo / ".git/worktrees/linked").mkdir(parents=True)
        linked.mkdir()
        (linked / ".git").write_text(f"gitdir: {main_repo}/.git/worktrees/linked\n")
        (plain / ".git").mkdir(parents=True)
        # (tool, cwd, command or file path, blocked)
        worktree_cases = [
            ("Bash", main_repo, "git checkout -b x", True),
            ("Bash", tmp, "cd main && git commit -m x", True),
            ("Bash", tmp, f"git -C {main_repo} reset --hard", True),
            ("Bash", main_repo, "git status && git pull", False),
            ("Bash", linked, "git commit -m x", False),
            ("Bash", plain, "git checkout -b x", False),
            ("Edit", tmp, str(main_repo / "a.py"), True),
            ("Write", tmp, str(linked / "a.py"), False),
        ]
        for tool, cwd, what, want in worktree_cases:
            key = "command" if tool == "Bash" else "file_path"
            if run(WORKTREE, {"tool_name": tool, "cwd": str(cwd), "tool_input": {key: what}}) != want:
                failures.append(f"{WORKTREE.name}: {tool} {what!r} should be {'blocked' if want else 'allowed'}")

    for f in failures:
        print(f, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
