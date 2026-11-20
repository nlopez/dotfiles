# Managed by chezmoi — source: home/dot_config/pr-box/pr_tracking.py
# PR tracking for coding-agent sessions, shared by every agent adapter (Claude
# Code hooks, the pi extension), pr_float.py and the Claude status line.
#
# Session PRs: adapters append PR URLs to sessions/<session_id>.json (or replace
# the list, see set_session); Claude's adapter also backfills them from the
# session transcript on resume.
# PR status: `gh pr view` results are cached per PR (or per repo+branch) and
# refreshed by a detached `python3 pr_tracking.py refresh ...` so the status
# line never waits on the network.
# PR notifications: while the box is open, pr_float.py calls notice_changes on
# every tick; a CI failure, approval, change request, merge or close, or a commit
# pushed from outside the session is queued in inbox/<session_id>.jsonl,
# and each agent's adapter delivers it with drain (Claude: hooks/pr-notify.py,
# pi: the pr-tracker extension).
# Event log: every session's watches (PRs starting or stopping being tracked)
# and status events are appended to $XDG_STATE_HOME/pr-box/events.jsonl
# (`pr_box.py log` prints it).
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
    "pr-box",
)
PR_URL = re.compile(r"https://[\w.-]+/[\w.-]+/[\w.-]+/pull/\d+")
FIELDS = "number,url,state,isDraft,reviewDecision,statusCheckRollup,headRefOid"
# Status refresh intervals, in seconds.
ACTIVE_TTL = 30  # checks running, failing or not reported yet
SETTLED_TTL = 300  # open with every check green: only review state can change
NO_PR_TTL = 120  # a branch without a PR yet
CLOSED_TTL = 3600  # merged or closed
HOT_TTL = 20  # right after a push or gh pr command
HOT_WINDOW = 180
# A refresh that has not finished within this window is assumed dead.
PENDING_TTL = 30
# A PR head change seen within this window after the session's own git push is
# taken to be that push, not a commit from someone else.
OWN_PUSH_WINDOW = 600


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


def _session_path(session_id, kind="sessions", ext=".json"):
    return _path(kind, re.sub(r"[^\w.-]", "_", session_id) + ext)


LOG = os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
    "pr-box",
    "events.jsonl",
)


def log(kind, session_id, url, text=""):
    """Append one watch or event to the cross-session log; never fails the caller."""
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, "session": session_id, "url": url}
    if text:
        entry["text"] = text
    with contextlib.suppress(OSError):
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")


def read_log(limit=50):
    """The last limit log lines, formatted one per line."""
    try:
        with open(LOG) as f:
            tail = f.readlines()[-limit:]
    except OSError:
        return ""
    out = []
    for line in tail:
        with contextlib.suppress(ValueError):
            e = json.loads(line)
            detail = f"  {e['text']}" if e.get("text") else ""
            out.append(f"{e.get('time')}  {e.get('kind'):<7}  {e.get('session')}  {e.get('url')}{detail}")
    return "\n".join(out)


def record(session_id, url):
    path = _session_path(session_id)
    urls = _read_json(path, [])
    if url not in urls:
        _write_json(path, urls + [url])
        log("watch", session_id, url)


def set_session(session_id, urls):
    """Replace the session's PR list, for agents whose history can be rewound."""
    path = _session_path(session_id)
    before = _read_json(path, [])
    urls = list(dict.fromkeys(urls))
    _write_json(path, urls)
    for url in urls:
        if url not in before:
            log("watch", session_id, url)
    for url in before:
        if url not in urls:
            log("unwatch", session_id, url)


def session_prs(session_id):
    return _read_json(_session_path(session_id), []) if session_id else []


def _key(*parts):
    return hashlib.sha1("\0".join(parts).encode()).hexdigest()[:16]


def _ttl(cached):
    """How long a cached status stays fresh: short while CI is moving, long once settled."""
    if cached is None:
        return 0
    state = cached.get("state")
    if not cached:
        return NO_PR_TTL
    if state in ("MERGED", "CLOSED"):
        return CLOSED_TTL
    return ACTIVE_TTL if checks(cached) in ("pending", "fail", "") else SETTLED_TTL


def _status(cache_name, cwd, target):
    """Cached PR dict, {} when there is no PR, None when not fetched yet."""
    path = _path("status", cache_name + ".json")
    cached = _read_json(path)
    age = time.time() - os.path.getmtime(path) if cached is not None else None
    ttl = _ttl(cached)
    if cached is not None and time.time() - _mtime(_path("status", ".hot")) < HOT_WINDOW:
        ttl = min(ttl, HOT_TTL)
    if age is None or age > ttl:
        _spawn_refresh(path, cwd, target)
    return cached


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def invalidate():
    """A push or gh pr command probably changed PR state: re-poll soon, fast for a while.

    CI starts a few seconds after a push, so statuses are marked stale and polled
    at HOT_TTL for HOT_WINDOW instead of waiting out the long settled interval.
    """
    os.makedirs(_path("status"), exist_ok=True)
    with open(_path("status", ".hot"), "w"):
        pass
    for name in os.listdir(_path("status")):
        if name.endswith(".json"):
            with contextlib.suppress(OSError):
                os.utime(_path("status", name), (0, 0))


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
    env = dict(os.environ)
    m = re.match(r"https://([\w.-]+/[\w.-]+/[\w.-]+)/pull/", target or "")
    if m:
        # Lets a multi-account gh wrapper pick the account that owns the repo.
        env["GH_REPO"] = m.group(1)
    try:
        out = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            _write_json(path, json.loads(out.stdout))
        elif "no pull requests found" in out.stderr.lower():
            _write_json(path, {})
    finally:
        with contextlib.suppress(OSError):
            os.remove(path + ".pending")


# Merge-readiness gates that stay pending until the PR merges, and the roll-up
# that mirrors them; neither says anything about the code.
GATE_CHECKS = {"devflow/mergegate", "ensure-ci-success"}


def real_checks(pr):
    return [i for i in pr.get("statusCheckRollup") or [] if (i.get("name") or i.get("context")) not in GATE_CHECKS]


def check_counts(pr):
    """(passed, total) over the checks that matter."""
    rollup = real_checks(pr)
    ok = {"SUCCESS", "NEUTRAL", "SKIPPED"}
    return sum(1 for i in rollup if (i.get("conclusion") or i.get("state") or "") in ok), len(rollup)


def checks(pr):
    """'pass', 'fail', 'pending' or '' from a statusCheckRollup."""
    rollup = real_checks(pr)
    if not rollup:
        return ""
    pending = False
    for item in rollup:
        result = item.get("conclusion") or item.get("state") or ""
        if result in FAILED:
            return "fail"
        if item.get("status", "COMPLETED") != "COMPLETED" or result in ("PENDING", "EXPECTED", ""):
            pending = True
    return "pending" if pending else "pass"


FAILED = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
REVIEW_EVENTS = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes requested"}


def note_push(session_id):
    """Record that the session just ran git push, so the head change it causes is not
    reported as a commit from outside the session."""
    if session_id:
        _write_json(_session_path(session_id, "pushes"), {"time": time.time()})


def _pushed_recently(session_id):
    last = (_read_json(_session_path(session_id, "pushes"), {}) or {}).get("time", 0)
    return time.time() - last < OWN_PUSH_WINDOW


def notice_changes(session_id, prs):
    """Queue a notification for each PR that was just merged or closed, and for each
    open PR whose CI just failed, that was just approved or had changes requested,
    or whose head moved to a commit the session did not push.

    Each PR's last seen state, head, CI and review state is kept per session; a PR
    seen for the first time only sets that baseline, so tracking an already-approved
    PR is not reported. PRs whose status has not been fetched yet are skipped.
    """
    if not session_id:
        return
    path = _session_path(session_id, "seen")
    seen = _read_json(path, {})
    now, events = {}, []
    for pr in prs:
        url = pr.get("url")
        if not url or "state" not in pr:
            if url in seen:
                now[url] = seen[url]
            continue
        state = pr.get("state") or ""
        head = pr.get("headRefOid") or ""
        cur = {"checks": checks(pr), "review": pr.get("reviewDecision") or "", "state": state, "head": head}
        now[url] = cur
        before = seen.get(url)
        if before is None:
            continue
        if before.get("state") == "OPEN" and state in ("MERGED", "CLOSED"):
            events.append((url, state.lower()))
        if state != "OPEN":
            continue
        if head and before.get("head") and head != before["head"] and not _pushed_recently(session_id):
            events.append((url, f"new commit {head[:10]} pushed from outside this session"))
        if cur["checks"] == "fail" and before.get("checks") != "fail":
            failed = [i for i in real_checks(pr) if (i.get("conclusion") or i.get("state")) in FAILED]
            names = [i.get("name") or i.get("context") or "?" for i in failed]
            events.append((url, f"CI failed ({', '.join(names)})"))
        if cur["review"] != before.get("review") and cur["review"] in REVIEW_EVENTS:
            events.append((url, REVIEW_EVENTS[cur["review"]]))
    if now != seen:
        _write_json(path, now)
    if events:
        for url, text in events:
            log("event", session_id, url, text)
        os.makedirs(_path("inbox"), exist_ok=True)
        with open(inbox_path(session_id), "a") as f:
            f.write("".join(json.dumps({"time": time.time(), "text": f"{u}: {t}"}) + "\n" for u, t in events))


def inbox_path(session_id):
    return _session_path(session_id, "inbox", ".jsonl")


def drain(session_id):
    """Take the session's queued PR notifications as one message, or '' if none."""
    path = inbox_path(session_id)
    taken = f"{path}.{os.getpid()}.taken"
    try:
        os.rename(path, taken)
    except OSError:
        return ""
    try:
        with open(taken) as f:
            events = [json.loads(line)["text"] for line in f if line.strip()]
    except Exception:
        events = []
    finally:
        with contextlib.suppress(OSError):
            os.remove(taken)
    if not events:
        return ""
    return (
        "[PR box] A PR this session tracks changed status. This is an automated notice, not a message"
        ' from the user. Begin your reply with one line that starts with "PR update:" and names the'
        " PR and the change, so the user can see you are reacting to it, then handle it.\n"
        + "\n".join(f"- {e}" for e in events)
    )


def status_lines(session_id):
    """One line per PR the session tracks, from the cached status, for agents to read."""
    out = []
    for url in session_prs(session_id):
        pr = url_pr(url)
        if pr is None:
            out.append(f"{url}  status not fetched yet")
            continue
        if not pr:
            out.append(f"{url}  not found")
            continue
        state = pr.get("state") or "?"
        if state == "OPEN" and pr.get("isDraft"):
            state = "DRAFT"
        passed, total = check_counts(pr)
        result = checks(pr) or "none"
        failed = [
            i.get("name") or i.get("context") or "?"
            for i in real_checks(pr)
            if (i.get("conclusion") or i.get("state")) in FAILED
        ]
        parts = [
            url,
            state,
            f"head {(pr.get('headRefOid') or '?')[:10]}",
            f"checks {result} {passed}/{total}",
        ]
        if failed:
            parts.append(f"failing: {', '.join(failed)}")
        if pr.get("reviewDecision"):
            parts.append(f"review {pr['reviewDecision'].lower()}")
        out.append("  ".join(parts))
    return "\n".join(out) or "no PRs tracked"


def repo_of(url):
    m = re.match(r"https://[\w.-]+/[\w.-]+/([\w.-]+)/pull/", url or "")
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
BOLD = 1
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
