# Managed by chezmoi — source: home/dot_config/claude/pr_tracking.py
# PR tracking shared by statusline.py and hooks/track-prs.py.
#
# Session PRs: hooks/track-prs.py appends PR URLs to sessions/<session_id>.json.
# PR status: `gh pr view` results are cached per PR (or per repo+branch) and
# refreshed by a detached `python3 pr_tracking.py refresh ...` so the status
# line never waits on the network.
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time

CACHE = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "claude",
    "pr-tracking",
)
PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
FIELDS = "number,url,state,isDraft,reviewDecision,statusCheckRollup"
OPEN_TTL = 60
CLOSED_TTL = 3600
# A refresh that has not finished within this window is assumed dead.
PENDING_TTL = 30


def _path(*parts):
    return os.path.join(CACHE, *parts)


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(value, f)
    os.replace(tmp, path)


def _session_path(session_id):
    return _path("sessions", re.sub(r"[^\w.-]", "_", session_id) + ".json")


def record(session_id, url):
    path = _session_path(session_id)
    urls = _read_json(path, [])
    if url not in urls:
        _write_json(path, urls + [url])


def session_prs(session_id):
    return _read_json(_session_path(session_id), []) if session_id else []


def _key(*parts):
    return hashlib.sha1("\0".join(parts).encode()).hexdigest()[:16]


def _status(cache_name, cwd, target):
    """Cached PR dict, {} when there is no PR, None when not fetched yet."""
    path = _path("status", cache_name + ".json")
    cached = _read_json(path)
    age = time.time() - os.path.getmtime(path) if cached is not None else None
    ttl = OPEN_TTL if (cached or {}).get("state") in (None, "OPEN") else CLOSED_TTL
    if age is None or age > ttl:
        _spawn_refresh(path, cwd, target)
    return cached


def _spawn_refresh(path, cwd, target):
    pending = path + ".pending"
    try:
        if time.time() - os.path.getmtime(pending) < PENDING_TTL:
            return
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(pending, "w").close()
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "refresh", path, cwd, target],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def branch_pr(cwd, common_dir, branch):
    return _status("branch-" + _key(common_dir, branch), cwd, "")


def url_pr(url):
    return _status("url-" + _key(url), os.path.expanduser("~"), url)


def refresh(path, cwd, target):
    args = ["gh", "pr", "view", *([target] if target else []), "--json", FIELDS]
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            _write_json(path, json.loads(out.stdout))
        elif "no pull requests found" in out.stderr.lower():
            _write_json(path, {})
    finally:
        with contextlib.suppress(OSError):
            os.remove(path + ".pending")


def checks(pr):
    """'pass', 'fail', 'pending' or '' from a statusCheckRollup."""
    rollup = pr.get("statusCheckRollup") or []
    if not rollup:
        return ""
    failed = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
    pending = False
    for item in rollup:
        result = item.get("conclusion") or item.get("state") or ""
        if result in failed:
            return "fail"
        if item.get("status", "COMPLETED") != "COMPLETED" or result in ("PENDING", "EXPECTED", ""):
            pending = True
    return "pending" if pending else "pass"


def repo_of(url):
    m = re.match(r"https://github\.com/[\w.-]+/([\w.-]+)/pull/", url or "")
    return m.group(1) if m else ""


def resolve_branch_pr(session_id, cwd):
    """Record the current branch's PR in cwd, if it has one (runs detached)."""
    out = subprocess.run(
        ["gh", "pr", "view", "--json", "url", "-q", ".url"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15,
    )
    url = out.stdout.strip()
    if out.returncode == 0 and PR_URL.fullmatch(url):
        record(session_id, url)


if __name__ == "__main__":
    if sys.argv[1:2] == ["refresh"]:
        refresh(*sys.argv[2:5])
    elif sys.argv[1:2] == ["resolve"]:
        resolve_branch_pr(*sys.argv[2:4])
