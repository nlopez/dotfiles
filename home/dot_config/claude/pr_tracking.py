# Managed by chezmoi — source: home/dot_config/claude/pr_tracking.py
# PR tracking shared by statusline.py, pr_float.py and hooks/track-prs.py.
#
# Session PRs: hooks/track-prs.py appends PR URLs to sessions/<session_id>.json,
# and on resume backfills them from the session transcript.
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


def git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=1)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def prs(session_id, cwd, common, branch):
    """[(pr, is_current_branch)]: the branch's PR first, then the session's others."""
    out = []
    current = None
    if common and branch and branch not in ("main", "master"):
        current = branch_pr(cwd, common, branch)
        if current:
            out.append((current, True))
    for url in session_prs(session_id):
        if url != (current or {}).get("url"):
            out.append(({"number": url.rsplit("/", 1)[-1], **(url_pr(url) or {}), "url": url}, False))
    return out


RESET = "\033[0m"
# Basic ANSI SGR codes (30-37 / 90-97) so colours follow the terminal theme.
MAGENTA, BLUE, CYAN, GREEN, YELLOW, RED, WHITE, DIM = 35, 34, 36, 32, 33, 31, 37, 90
CHECK_GLYPH = {"pass": (GREEN, "✓"), "fail": (RED, "✗"), "pending": (YELLOW, "…")}
REVIEW = {"APPROVED": (GREEN, "approved"), "CHANGES_REQUESTED": (RED, "changes")}


def c(code, text):
    return f"\033[{code}m{text}{RESET}"


def link(url, text):
    """OSC 8 hyperlink, so the label opens the PR on click."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\" if url else text


def label(pr, prefix=""):
    """'#12 draft ✓ approved'-style label; state and review only when notable."""
    bits = [c(GREEN, f"{prefix}#{pr.get('number')}")]
    state = pr.get("state")
    if state == "MERGED":
        bits.append(c(MAGENTA, "merged"))
    elif state == "CLOSED":
        bits.append(c(RED, "closed"))
    else:
        if pr.get("isDraft"):
            bits.append(c(DIM, "draft"))
        glyph = CHECK_GLYPH.get(checks(pr))
        if glyph:
            bits.append(c(*glyph))
        review = REVIEW.get(pr.get("reviewDecision"))
        if review:
            bits.append(c(*review))
    return link(pr.get("url"), " ".join(bits))


PR_COMMAND = re.compile(r"\bgh\s+pr\s+(create|ready|edit|merge)\b")
PUSH_COMMAND = re.compile(r"\bgit\b[^;&|]*\bpush\b")


def command_prs(command, output):
    """PR URLs a gh pr create/ready/edit/merge command printed."""
    return list(dict.fromkeys(PR_URL.findall(output))) if PR_COMMAND.search(command) else []


def spawn_resolve(session_id, cwd):
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "resolve", session_id, cwd],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def backfill(session_id, transcript_path):
    """Record PRs from a transcript's Bash calls, as the PostToolUse hook would have.

    Pushes resolve each pushed directory's current branch PR, which may differ
    from the branch pushed at the time if the directory has since switched.
    """
    commands, push_dirs = {}, []
    with open(transcript_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    commands[block.get("id")] = (block.get("input") or {}).get("command") or ""
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in commands:
                    command = commands.pop(block["tool_use_id"])
                    output = block.get("content")
                    output = output if isinstance(output, str) else json.dumps(output)
                    for url in command_prs(command, output):
                        record(session_id, url)
                    cwd = entry.get("cwd")
                    if PUSH_COMMAND.search(command) and cwd and cwd not in push_dirs:
                        push_dirs.append(cwd)
    for cwd in push_dirs:
        if os.path.isdir(cwd):
            with contextlib.suppress(Exception):
                resolve_branch_pr(session_id, cwd)


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
    elif sys.argv[1:2] == ["backfill"]:
        backfill(*sys.argv[2:4])
