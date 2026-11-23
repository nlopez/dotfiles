#!/usr/bin/env python3
"""Pre-commit hook: bump VERSION in home/dot_config/argus-pr/pr_float.py when Argus files are staged."""

import re
import subprocess
import sys
from pathlib import Path

PR_FLOAT = "home/dot_config/argus-pr/pr_float.py"
ARGUS_RE = re.compile(r"^(home/dot_config/argus-pr/|home/\.private/work/argus-pr-.*\.age$)")
VERSION_RE = re.compile(r"^VERSION\s*=\s*(\d+)\b", re.MULTILINE)


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _extract_version(text):
    m = VERSION_RE.search(text)
    return int(m.group(1)) if m else None


def main():
    staged = _git("diff", "--cached", "--name-only").stdout.splitlines()
    if not any(ARGUS_RE.match(p) for p in staged):
        return 0

    head = _git("show", f"HEAD:{PR_FLOAT}")
    if head.returncode != 0:
        return 0
    head_ver = _extract_version(head.stdout)

    path = Path(PR_FLOAT)
    current_text = path.read_text()
    cur_ver = _extract_version(current_text)
    if head_ver is None or cur_ver is None:
        print(f"argus-pr-version: could not parse VERSION in {PR_FLOAT}", file=sys.stderr)
        return 1

    if cur_ver > head_ver:
        return 0

    new_ver = head_ver + 1
    updated = VERSION_RE.sub(f"VERSION = {new_ver}", current_text, count=1)
    path.write_text(updated)
    add = _git("add", PR_FLOAT)
    if add.returncode != 0:
        print(add.stderr, file=sys.stderr)
        return 1
    print(f"argus-pr-version: bumped VERSION {head_ver} -> {new_ver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
