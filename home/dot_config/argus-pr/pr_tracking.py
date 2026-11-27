# Managed by chezmoi — source: home/dot_config/argus-pr/pr_tracking.py
# PR tracking for coding-agent sessions, shared by every agent adapter (Claude
# Code hooks, the pi extension), pr_float.py and the Claude status line.
#
# Session PRs, baselines, push timestamps, event log and per-consumer cursors
# live in SQLite ($XDG_CACHE_HOME/argus-pr/state.db, WAL mode); Claude's
# adapter also backfills PRs from the session transcript on resume.
# PR status: `gh pr view` results are cached per PR (or per repo+branch) and
# refreshed by a detached `python3 pr_tracking.py refresh ...` so the status
# line never waits on the network.
# PR notifications: while the box is open, pr_float.py calls notice_changes on
# every tick; CI finishing (passed, or failed once every check is done), an approval or
# change request, a merge or close, post-merge CI failing or passing, or a
# commit pushed from outside the session is appended to the `events` table and
# touches `notify` so agent adapters wake and advance their cursor with drain
# (Claude: hooks/pr-notify.py, pi: the pr-tracker extension).
import base64
import calendar
import contextlib
import glob
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

CACHE = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "argus-pr",
)
PR_URL = re.compile(r"https://[\w.-]+/[\w.-]+/[\w.-]+/pull/\d+")
FIELDS = (
    "number,url,state,isDraft,reviewDecision,statusCheckRollup,headRefOid,"
    "mergeCommit,mergedAt,mergeable,author,comments,reviews"
)
# Status refresh intervals, in seconds.
ACTIVE_TTL = 15  # checks running, failing or not reported yet
SETTLED_TTL = 300  # open with every check green: only review state can change
NO_PR_TTL = 120  # a branch without a PR yet
CLOSED_TTL = 3600  # merged or closed
HOT_TTL = 10  # right after a push or gh pr command
HOT_WINDOW = 180
ERROR_TTL = 60  # retry interval after a failed gh check
# A refresh that has not finished within this window is assumed dead.
PENDING_TTL = 30
# A PR head change seen within this window after the session's own git push is
# taken to be that push, not a commit from someone else.
OWN_PUSH_WINDOW = 600
# How long after a merge the merge commit's checks (post-merge CI, such as
# Terraform applies) are fetched and reported.
POST_MERGE_WINDOW = 6 * 3600


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


DB_PATH = os.path.join(CACHE, "state.db")
NOTIFY_PATH = os.path.join(CACHE, "notify")

# Bump when _SCHEMA changes, so existing databases pick up the change.
SCHEMA_VERSION = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_prs (
    session_id TEXT NOT NULL,
    url        TEXT NOT NULL,
    added_at   REAL NOT NULL,
    PRIMARY KEY (session_id, url)
);
CREATE TABLE IF NOT EXISTS session_pushes (
    session_id TEXT PRIMARY KEY,
    pushed_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS seen (
    session_id TEXT NOT NULL,
    url        TEXT NOT NULL,
    state_json TEXT NOT NULL,
    PRIMARY KEY (session_id, url)
);
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    kind       TEXT NOT NULL,
    session_id TEXT NOT NULL,
    url        TEXT NOT NULL,
    text       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, kind, id);
CREATE TABLE IF NOT EXISTS comments (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    url     TEXT NOT NULL,
    cid     TEXT NOT NULL,
    author  TEXT NOT NULL,
    path    TEXT NOT NULL DEFAULT '',
    line    INTEGER,
    created TEXT NOT NULL DEFAULT '',
    body    TEXT NOT NULL,
    UNIQUE (url, cid)
);
CREATE TABLE IF NOT EXISTS cursors (
    session_id    TEXT NOT NULL,
    consumer      TEXT NOT NULL,
    last_event_id INTEGER NOT NULL,
    PRIMARY KEY (session_id, consumer)
);
"""


def _migrate_legacy(conn):
    """Best-effort one-time import of legacy sessions/*.json and seen/*.json on fresh DB."""
    now = time.time()
    for path in glob.glob(_path("sessions", "*.json")):
        sid = os.path.splitext(os.path.basename(path))[0]
        urls = _read_json(path, [])
        if isinstance(urls, list):
            for url in urls:
                if isinstance(url, str):
                    conn.execute(
                        "INSERT OR IGNORE INTO session_prs(session_id, url, added_at) VALUES (?, ?, ?)",
                        (sid, url, now),
                    )
    for path in glob.glob(_path("seen", "*.json")):
        sid = os.path.splitext(os.path.basename(path))[0]
        data = _read_json(path, {})
        if isinstance(data, dict):
            for url, state in data.items():
                if isinstance(url, str) and isinstance(state, dict):
                    conn.execute(
                        "INSERT OR IGNORE INTO seen(session_id, url, state_json) VALUES (?, ?, ?)",
                        (sid, url, json.dumps(state)),
                    )


@contextlib.contextmanager
def _db():
    os.makedirs(CACHE, exist_ok=True)
    fresh = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    try:
        conn.execute("PRAGMA synchronous=NORMAL")
        # WAL mode and the schema persist in the file; set them up once per schema version.
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        if fresh:
            conn.execute("BEGIN IMMEDIATE")
            try:
                _migrate_legacy(conn)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
        yield conn
    finally:
        conn.close()


def _touch_notify(event_id):
    with contextlib.suppress(OSError):
        os.makedirs(CACHE, exist_ok=True)
        tmp = f"{NOTIFY_PATH}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            f.write(f"{event_id}\n")
        os.replace(tmp, NOTIFY_PATH)


def _format_event(ts, kind, session_id, url, text):
    when = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))
    detail = f"  {text}" if text else ""
    return f"{when}  {kind:<7}  {session_id}  {url}{detail}"


def log(kind, session_id, url, text=""):
    """Append one watch or event to the cross-session log; never fails the caller."""
    with contextlib.suppress(Exception), _db() as conn:
        conn.execute(
            "INSERT INTO events(ts, kind, session_id, url, text) VALUES (?, ?, ?, ?, ?)",
            (time.time(), kind, session_id, url, text or ""),
        )


def read_log(limit=50):
    """The last limit log lines, formatted one per line."""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT ts, kind, session_id, url, text FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception:
        return ""
    return "\n".join(_format_event(*r) for r in reversed(rows))


def session_events(session_id, limit=20):
    """Recent status events for one session, without advancing any cursor."""
    if not session_id:
        return ""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT ts, url, text FROM events WHERE session_id = ? AND kind = 'event' ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
    except Exception:
        return ""
    out = []
    for ts, url, text in reversed(rows):
        when = time.strftime("%H:%M:%S", time.localtime(ts))
        out.append(f"{when}  {url}: {text}")
    return "\n".join(out) or "no recent events"


def record(session_id, url):
    if not session_id or not url:
        return
    now = time.time()
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO session_prs(session_id, url, added_at) VALUES (?, ?, ?)",
                (session_id, url, now),
            )
            if cur.rowcount:
                conn.execute(
                    "INSERT INTO events(ts, kind, session_id, url, text) VALUES (?, 'watch', ?, ?, '')",
                    (now, session_id, url),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def set_session(session_id, urls):
    """Replace the session's PR list, for agents whose history can be rewound."""
    if not session_id:
        return
    urls = list(dict.fromkeys(urls))
    now = time.time()
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            before = [
                r[0]
                for r in conn.execute(
                    "SELECT url FROM session_prs WHERE session_id = ? ORDER BY added_at, url",
                    (session_id,),
                ).fetchall()
            ]
            added = [u for u in urls if u not in before]
            removed = [u for u in before if u not in urls]
            for url in added:
                conn.execute(
                    "INSERT OR IGNORE INTO session_prs(session_id, url, added_at) VALUES (?, ?, ?)",
                    (session_id, url, now),
                )
                conn.execute(
                    "INSERT INTO events(ts, kind, session_id, url, text) VALUES (?, 'watch', ?, ?, '')",
                    (now, session_id, url),
                )
            for url in removed:
                conn.execute("DELETE FROM session_prs WHERE session_id = ? AND url = ?", (session_id, url))
                conn.execute("DELETE FROM seen WHERE session_id = ? AND url = ?", (session_id, url))
                conn.execute(
                    "INSERT INTO events(ts, kind, session_id, url, text) VALUES (?, 'unwatch', ?, ?, '')",
                    (now, session_id, url),
                )
            if removed:
                conn.execute("DELETE FROM comments WHERE url NOT IN (SELECT url FROM session_prs)")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def reset_session(session_id):
    """Wipe a session's tracked PRs, notification baselines, push state and advance cursors."""
    if not session_id:
        return
    set_session(session_id, [])
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM seen WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM session_pushes WHERE session_id = ?", (session_id,))
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]
            conn.execute(
                "INSERT INTO cursors(session_id, consumer, last_event_id) VALUES (?, 'agent', ?)"
                " ON CONFLICT(session_id, consumer) DO UPDATE SET last_event_id = excluded.last_event_id",
                (session_id, max_id),
            )
            conn.execute(
                "UPDATE cursors SET last_event_id = ? WHERE session_id = ?",
                (max_id, session_id),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def session_prs(session_id):
    if not session_id:
        return []
    try:
        with _db() as conn:
            return [
                r[0]
                for r in conn.execute(
                    "SELECT url FROM session_prs WHERE session_id = ? ORDER BY added_at, url",
                    (session_id,),
                ).fetchall()
            ]
    except Exception:
        return []


def _key(*parts):
    return hashlib.sha1("\0".join(parts).encode()).hexdigest()[:16]


def _ttl(cached):
    """How long a cached status stays fresh: short while CI is moving, long once settled."""
    if cached is None:
        return 0
    if cached.get("_error"):
        return ERROR_TTL
    if not cached:
        return NO_PR_TTL
    state = cached.get("state")
    if state == "MERGED" and _recently_merged(cached):
        return ACTIVE_TTL if merge_checks(cached) in ("pending", "") else SETTLED_TTL
    if state in ("MERGED", "CLOSED"):
        return CLOSED_TTL
    return ACTIVE_TTL if checks(cached) in ("pending", "fail", "") else SETTLED_TTL


def _status(cache_name, cwd, target):
    """Cached PR dict, {} when there is no PR, None when not fetched yet."""
    path = _path("status", cache_name + ".json")
    cached = _read_json(path)
    now = time.time()
    mtime = _mtime(path) if cached is not None else None
    age = now - mtime if mtime is not None else None
    ttl = _ttl(cached)
    if cached is not None and now - _mtime(_path("status", ".hot")) < HOT_WINDOW:
        ttl = min(ttl, HOT_TTL)
    if age is None or age > ttl:
        _spawn_refresh(path, cwd, target)
    if not cached:
        return cached
    pending_mtime = _mtime(path + ".pending")
    refreshing = pending_mtime > 0 and (now - pending_mtime) < PENDING_TTL
    return {**cached, "_next_check": mtime + ttl, "_refreshing": refreshing}


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


def _run_gh(args, cwd, env=None):
    # Run via the user's login shell so non-interactive parents (e.g. rex server)
    # still get the user's PATH and gh shim routing.
    shell = os.environ.get("SHELL") or "/bin/sh"
    return subprocess.run(
        [shell, "-lc", 'exec "$@"', "_", "gh", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _short_error(text, limit=120):
    """First non-empty line of an error message, whitespace-collapsed."""
    for line in (text or "").splitlines():
        line = " ".join(line.split())
        if line:
            return line[:limit]
    return ""


def _record_error(path, target, err):
    prev = _read_json(path)
    data = dict(prev) if isinstance(prev, dict) else {}
    if data.get("_error") != err:
        log("error", "-", target, err)
    data["_error"] = err
    _write_json(path, data)


def _plugin_fetch(target, env, cwd):
    """Let an adapter plugin fetch target before falling back to gh pr view."""
    if not target:
        return None
    for plugin in _plugins():
        fn = getattr(plugin, "fetch", None)
        if not callable(fn):
            continue
        try:
            pr = fn(target, env, cwd)
            if isinstance(pr, dict):
                return pr
        except Exception:
            continue
    return None


def refresh(path, cwd, target):
    args = ["pr", "view", *([target] if target else []), "--json", FIELDS]
    env = dict(os.environ)
    m = re.match(r"https://([\w.-]+/[\w.-]+/[\w.-]+)/pull/", target or "")
    if m:
        # Lets a multi-account gh wrapper pick the account that owns the repo.
        env["GH_REPO"] = m.group(1)
    try:
        pr = _plugin_fetch(target, env, cwd)
        if pr is None:
            out = _run_gh(args, cwd=cwd, env=env)
            if out.returncode == 0:
                pr = json.loads(out.stdout)
            elif "no pull requests found" in out.stderr.lower():
                _write_json(path, {})
                return
            else:
                err = _short_error(out.stderr) or _short_error(out.stdout) or f"gh exited {out.returncode}"
                _record_error(path, target or cwd, err)
                return
        if pr.get("state") == "OPEN" and "reviewComments" not in pr:
            try:
                pr["reviewComments"] = _review_comments(pr, env, cwd)
            except Exception as e:
                prev = _read_json(path)
                if isinstance(prev, dict) and "reviewComments" in prev:
                    pr["reviewComments"] = prev["reviewComments"]
                err = _short_error(str(e)) or type(e).__name__
                if not isinstance(prev, dict) or prev.get("_error") != err:
                    log("error", "-", target or cwd, err)
                pr["_error"] = err
        if pr.get("state") == "MERGED" and _recently_merged(pr) and "mergeChecks" not in pr:
            try:
                pr["mergeChecks"] = _commit_checks(pr, env, cwd)
            except Exception as e:
                prev = _read_json(path)
                if isinstance(prev, dict) and prev.get("mergeChecks"):
                    pr["mergeChecks"] = prev["mergeChecks"]
                err = _short_error(str(e)) or type(e).__name__
                if not isinstance(prev, dict) or prev.get("_error") != err:
                    log("error", "-", target or cwd, err)
                pr["_error"] = err
        if not pr.pop("_skip_enrich", False):
            for plugin in _plugins():
                enrich = getattr(plugin, "enrich", None)
                if not callable(enrich):
                    continue
                try:
                    enrich(pr, env, cwd)
                except Exception as e:
                    prev = _read_json(path)
                    if isinstance(prev, dict):
                        for k in ("_review", "_notes"):
                            if k in prev and k not in pr:
                                pr[k] = prev[k]
                    err = _short_error(str(e)) or type(e).__name__
                    if not isinstance(prev, dict) or prev.get("_error") != err:
                        log("error", "-", target or cwd, err)
                    pr["_error"] = err
        arp = pr.get("_arp")
        if arp and arp.get("state") not in ("", "queued", "running") and pr.get("state") == "OPEN":
            n = arp.get("findings") or 0
            text = f"ARP: {n} finding{'s' * (n != 1)}" if arp["state"] != "failed" else "ARP: review failed"
            pr.setdefault("_notes", []).append(
                {"text": text, "color": "yellow" if n or arp["state"] == "failed" else "green"}
            )
        _write_json(path, pr)
    except subprocess.TimeoutExpired:
        _record_error(path, target or cwd, "gh timed out")
    except Exception as e:
        _record_error(path, target or cwd, _short_error(str(e)) or type(e).__name__)
    finally:
        with contextlib.suppress(OSError):
            os.remove(path + ".pending")


PLUGINS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
_loaded_plugins = None


def plugin_files():
    """Sorted paths to optional extension modules in plugins/*.py."""
    if not os.path.isdir(PLUGINS_DIR):
        return []
    return sorted(
        p
        for p in glob.glob(os.path.join(PLUGINS_DIR, "*.py"))
        if not os.path.basename(p).startswith("_") and os.path.getsize(p) > 0
    )


def _plugins():
    global _loaded_plugins
    if _loaded_plugins is not None:
        return _loaded_plugins
    loaded = []
    for path in plugin_files():
        name = "argus_pr_plugin_" + os.path.splitext(os.path.basename(path))[0]
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                loaded.append(mod)
        except Exception:
            continue
    _loaded_plugins = loaded
    return _loaded_plugins


def ignored_checks(pr):
    """Check names plugins exclude from CI pass/fail counts (e.g. merge-readiness gates)."""
    names = set()
    for plugin in _plugins():
        static = getattr(plugin, "IGNORED_CHECKS", None)
        if static:
            names.update(static)
        fn = getattr(plugin, "ignored_checks", None)
        if callable(fn):
            with contextlib.suppress(Exception):
                names.update(fn(pr) or ())
    return names


def review_state(pr):
    """Effective review / merge-readiness state for an open PR:
    'ready', 'approved', 'changes', 'blocked', 'needed', 'pending', or ''."""
    decision = pr.get("reviewDecision") or ""
    if decision == "CHANGES_REQUESTED":
        return "changes"
    if "_review" in pr:
        return pr["_review"]
    if decision == "APPROVED":
        return "approved"
    return "needed" if decision else ""


def _recently_merged(pr):
    merged = pr.get("mergedAt") or ""
    try:
        when = calendar.timegm(time.strptime(merged[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return False
    return time.time() - when < POST_MERGE_WINDOW


def _review_comments(pr, env, cwd):
    """Inline diff review comments on a PR, shaped like gh pr view comments."""
    m = re.match(r"https://[\w.-]+/([\w.-]+/[\w.-]+)/pull/(\d+)", pr.get("url") or "")
    if not m:
        return []
    # shortcut: fetches latest 100 inline comments without pagination; paginate if PRs routinely exceed 100.
    out = _run_gh(
        ["api", f"repos/{m.group(1)}/pulls/{m.group(2)}/comments?per_page=100&sort=created&direction=desc"],
        cwd=cwd,
        env=env,
    )
    if out.returncode != 0:
        raise RuntimeError(_short_error(out.stderr) or f"gh api review comments exited {out.returncode}")
    return [
        {
            "id": item["id"],
            "author": {"login": (item.get("user") or {}).get("login") or "?"},
            "body": item.get("body") or "",
            "path": item.get("path") or "",
            "line": item.get("line") or item.get("original_line"),
            "createdAt": item.get("created_at") or "",
            "authorAssociation": item.get("author_association") or "",
        }
        for item in json.loads(out.stdout or "[]")
        if item.get("id") is not None
    ]


def _commit_checks(pr, env, cwd):
    """The merge commit's statuses and check runs, shaped like statusCheckRollup."""
    sha = (pr.get("mergeCommit") or {}).get("oid") or ""
    m = re.match(r"https://[\w.-]+/([\w.-]+/[\w.-]+)/pull/", pr.get("url") or "")
    if not sha or not m:
        return []
    items = []
    for endpoint, key in (("status", "statuses"), ("check-runs", "check_runs")):
        out = _run_gh(
            ["api", f"repos/{m.group(1)}/commits/{sha}/{endpoint}?per_page=100", "--jq", f".{key}"],
            cwd=cwd,
            env=env,
        )
        if out.returncode != 0:
            raise RuntimeError(_short_error(out.stderr) or f"gh api {endpoint} exited {out.returncode}")
        for item in json.loads(out.stdout or "[]"):
            if key == "statuses":
                items.append({"context": item.get("context"), "state": (item.get("state") or "").upper()})
            else:
                items.append(
                    {
                        "name": item.get("name"),
                        "status": (item.get("status") or "").upper(),
                        "conclusion": (item.get("conclusion") or "").upper(),
                    }
                )
    return items


def real_checks(pr, key="statusCheckRollup"):
    skip = ignored_checks(pr)
    return [i for i in pr.get(key) or [] if (i.get("name") or i.get("context")) not in skip]


def check_counts(pr, key="statusCheckRollup"):
    """(passed, total) over the checks that matter."""
    rollup = real_checks(pr, key)
    ok = {"SUCCESS", "NEUTRAL", "SKIPPED"}
    return sum(1 for i in rollup if (i.get("conclusion") or i.get("state") or "") in ok), len(rollup)


def checks(pr, key="statusCheckRollup"):
    """'pass', 'fail', 'pending' or '' from a statusCheckRollup."""
    rollup = real_checks(pr, key)
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


def checks_settled(pr, key="statusCheckRollup"):
    """'pass', 'fail', 'pending' or '' — only reports 'fail' once no checks are still running."""
    rollup = real_checks(pr, key)
    if not rollup:
        return ""
    failed = False
    for item in rollup:
        result = item.get("conclusion") or item.get("state") or ""
        if item.get("status", "COMPLETED") != "COMPLETED" or result in ("PENDING", "EXPECTED", ""):
            return "pending"
        if result in FAILED:
            failed = True
    return "fail" if failed else "pass"


def merge_checks(pr):
    """checks() over the merge commit's checks, fetched for a while after a merge."""
    return checks(pr, "mergeChecks")


def _failed_names(pr, key="statusCheckRollup"):
    return [
        i.get("name") or i.get("context") or "?"
        for i in real_checks(pr, key)
        if (i.get("conclusion") or i.get("state")) in FAILED
    ]


FAILED = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
REVIEW_EVENTS = {"ready": "ready to merge", "approved": "approved", "changes": "changes requested"}
_LEGACY_REVIEW = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes", "REVIEW_REQUIRED": "needed"}


def note_push(session_id):
    """Record that the session just ran git push, so the head change it causes is not
    reported as a commit from outside the session."""
    if not session_id:
        return
    with _db() as conn:
        conn.execute(
            "INSERT INTO session_pushes(session_id, pushed_at) VALUES (?, ?)"
            " ON CONFLICT(session_id) DO UPDATE SET pushed_at = excluded.pushed_at",
            (session_id, time.time()),
        )


def _pushed_recently(session_id):
    if not session_id:
        return False
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT pushed_at FROM session_pushes WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return bool(row and (time.time() - row[0]) < OWN_PUSH_WINDOW)
    except Exception:
        return False


def _brief(body, limit=600):
    """A comment body without HTML comments, collapsed to one line and cut to limit characters."""
    text = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    text = re.sub(r"</?sub>|\*\*", "", re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def _database_id(node_id):
    """GitHub's numeric id for a GraphQL node id such as PRR_kwDO…, or node_id unchanged.

    gh pr view returns node ids; REST and the plugins return numeric ids. A node id
    is a type prefix and base64url msgpack of [0, repository id, object id]."""
    m = re.fullmatch(r"[A-Z]+_(kw[\w-]+)", str(node_id))
    if not m:
        return node_id
    try:
        raw = base64.urlsafe_b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4))
    except ValueError:
        return node_id
    sizes = {0xCC: 1, 0xCD: 2, 0xCE: 4, 0xCF: 8}
    if len(raw) < 2 or raw[0] != 0x93:
        return node_id
    values, pos = [], 1
    while pos < len(raw):
        tag = raw[pos]
        if tag < 0x80:
            values.append(tag)
            pos += 1
        elif tag in sizes and pos + 1 + sizes[tag] <= len(raw):
            values.append(int.from_bytes(raw[pos + 1 : pos + 1 + sizes[tag]], "big"))
            pos += 1 + sizes[tag]
        else:
            return node_id
    return values[2] if len(values) == 3 else node_id


def _login(author):
    """An author's login without the [bot] suffix that gh pr view leaves off."""
    login = (author or {}).get("login") or ""
    return login[: -len("[bot]")] if login.endswith("[bot]") else login


def _comment_key(key):
    """A stored kind:id comment key with any node id swapped for the numeric id."""
    kind, _, cid = key.partition(":")
    return f"{kind}:{_database_id(cid)}"


# Anyone can comment on a public repo; their text must not reach the agent as a task.
UNTRUSTED_AUTHORS = {"NONE", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "MANNEQUIN"}


def _trusted(item):
    """Whether a comment's author has a role in the repo, or is the ARP reviewer."""
    if item.get("authorAssociation") not in UNTRUSTED_AUTHORS:
        return True
    return _login(item.get("author")).startswith(ARP_AUTHOR)


def _comments(pr):
    """{kind:id: comment} of a PR's comments, inline review comments and review bodies, or None if not fetched.

    Comments from authors with no role in the repo are left out."""
    if not any(k in pr for k in ("comments", "reviews", "reviewComments")):
        return None
    groups = (
        ("c", pr.get("comments") or []),
        ("r", [r for r in (pr.get("reviews") or []) if r.get("body")]),
        ("rc", pr.get("reviewComments") or []),
    )
    return {
        f"{kind}:{_database_id(i['id'])}": {
            "who": _login(i.get("author")) or "?",
            "path": i.get("path") or "",
            "line": i.get("line"),
            "created": i.get("createdAt") or i.get("submittedAt") or "",
            "body": i.get("body") or "",
        }
        for kind, items in groups
        for i in items
        if i.get("id") is not None and _trusted(i)
    }


def _feedback(pr, comments):
    """The comments not written by the PR's author."""
    me = _login(pr.get("author"))
    return {k: v for k, v in comments.items() if v["who"] != me}


def _store_comments(url, comments):
    """Upsert a PR's comments; an edited body gets a new id so readers see it as unread."""
    with _db() as conn:
        have = dict(conn.execute("SELECT cid, body FROM comments WHERE url = ?", (url,)).fetchall())
        changed = [(k, v) for k, v in comments.items() if have.get(k) != v["body"]]
        if not changed:
            return
        conn.execute("BEGIN IMMEDIATE")
        try:
            for k, v in changed:
                conn.execute("DELETE FROM comments WHERE url = ? AND cid = ?", (url, k))
                conn.execute(
                    "INSERT INTO comments(url, cid, author, path, line, created, body) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (url, k, v["who"], v["path"], v["line"], v["created"], v["body"]),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def _set_comment_cursors(conn, session_id, last):
    """Advance the session's per-PR comment cursors to {url: comment id}."""
    for u, cid in last.items():
        conn.execute(
            "INSERT INTO cursors(session_id, consumer, last_event_id) VALUES (?, ?, ?)"
            " ON CONFLICT(session_id, consumer) DO UPDATE SET last_event_id = excluded.last_event_id",
            (session_id, "comments:" + u, cid),
        )


def mark_comments_read(session_id, url):
    """Treat every comment stored for url as already read by the session, e.g. those there when tracking began."""
    with _db() as conn:
        top = conn.execute("SELECT MAX(id) FROM comments WHERE url = ?", (url,)).fetchone()[0]
        if top is not None:
            _set_comment_cursors(conn, session_id, {url: top})


def read_comments(session_id, url=None, unread=True):
    """Full text of comments on the session's tracked PRs; with unread, only unread ones, advancing the cursors."""
    if not session_id:
        return ""
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                "SELECT c.id, c.url, c.cid, c.author, c.path, c.line, c.created, c.body FROM comments c"
                " JOIN session_prs s ON s.url = c.url AND s.session_id = ?"
                " LEFT JOIN cursors k ON k.session_id = s.session_id AND k.consumer = 'comments:' || c.url"
                " WHERE c.id > (CASE WHEN ? THEN COALESCE(k.last_event_id, 0) ELSE 0 END)"
                " AND (? IS NULL OR c.url = ?) ORDER BY c.id",
                (session_id, unread, url, url),
            ).fetchall()
            if unread and url is None:
                _set_comment_cursors(conn, session_id, {r[1]: r[0] for r in rows})
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    kinds = {"c": "comment", "r": "review", "rc": "inline comment"}
    out = []
    for _, u, cid, author, path, line, created, body in rows:
        where = f" on {path}:{line or '?'}" if path else ""
        out.append(f"### {u} {kinds.get(cid.split(':')[0], 'comment')} by {author}{where} {created}".rstrip())
        out.append(body.strip())
        out.append("")
    return "\n".join(out).strip()


def _ci_event(pr, settled, key="statusCheckRollup"):
    """The event text for CI that just finished, or '' while checks still run."""
    if settled == "pass":
        passed, total = check_counts(pr, key)
        return f"CI passed ({passed}/{total})"
    if settled == "fail":
        failed = sorted(set(_failed_names(pr, key)))
        return f"CI failed ({', '.join(failed)})" if failed else "CI failed"
    return ""


ARP_AUTHOR = "dd-agentic-review-platform"
ARP_WAIT = 120  # how long a finished review may wait for its inline comments to load


def _is_arp(comment):
    return comment["who"].startswith(ARP_AUTHOR)


def _notice_arp(arp, fb, arp_ids, before, cur, now_ts):
    """One event per finished ARP review, sent once its inline comments have loaded
    and listing them, or ''. ARP comments are kept out of the per-comment events:
    inline ones until the review's event carries them, summary bodies always.

    Sets cur's arp_reported (review id already announced), arp_since (when the
    unannounced review was first seen finished) and arp_shown (ARP comment ids
    that need no event of their own)."""
    shown = set(before.get("arp_shown", arp_ids))
    reported = before.get("arp_reported", arp.get("id") if before.get("arp") == cur["arp"] else None)
    rid, state = arp.get("id"), arp.get("state")
    cur["arp_reported"] = reported
    cur["arp_shown"] = sorted(shown | {i for i in arp_ids if not fb[i]["path"]})
    if not rid or rid == reported or state in (None, "", "queued", "running"):
        return ""
    since = before.get("arp_since") if before.get("arp") == cur["arp"] else None
    since = since or now_ts
    n = arp.get("findings") or 0
    inline = [i for i in arp_ids if fb[i]["path"] and i not in shown]
    loaded = len(inline) >= n or state != "issues_found"
    if not loaded and now_ts - since < ARP_WAIT:
        cur["arp_since"] = since
        return ""
    cur["arp_reported"] = rid
    cur["arp_shown"] = sorted(shown | set(arp_ids))
    if state == "failed":
        return "ARP review failed"
    if not n:
        return "ARP review: no findings"
    text = f"ARP review: {n} finding{'s' * (n != 1)}"
    if state == "completed_no_post":
        return f"{text} (not posted to GitHub; read them with agentic_review_get_findings)"
    if not loaded:
        text += f" ({len(inline)} loaded)"
    for i in inline:
        c = fb[i]
        text += f"\n  - {c['path']}:{c['line'] or '?'}: {_brief(c['body'], 200)}"
    return text


def notice_changes(session_id, prs):
    """Record an event for each PR that was just merged or closed, and for each
    open PR whose CI just finished (every check done: passed, or failed with the
    failing checks named), that was just approved or had changes requested, or whose
    head moved to a commit the session did not push.

    Each PR's last seen state, head, CI and review state is kept per session; a PR
    seen for the first time only sets that baseline, so tracking an already-approved
    PR is not reported. PRs whose status has not been fetched yet are skipped.
    """
    if not session_id:
        return
    with _db() as conn:
        seen = {
            url: json.loads(state_json)
            for url, state_json in conn.execute(
                "SELECT url, state_json FROM seen WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        }
    now_map, events = {}, []
    pushed_recently = _pushed_recently(session_id)
    for pr in prs:
        url = pr.get("url")
        if not url or "state" not in pr:
            if url in seen:
                now_map[url] = seen[url]
            continue
        state = pr.get("state") or ""
        head = pr.get("headRefOid") or ""
        cur = {
            "checks": checks_settled(pr),
            "review": review_state(pr),
            "state": state,
            "head": head,
            "merge_checks": checks_settled(pr, "mergeChecks"),
        }
        arp = pr.get("_arp") or {}
        cur["arp"] = [arp.get("id"), arp.get("state")]
        now_ts = time.time()
        comments = _comments(pr)
        fb = None
        if comments is not None:
            _store_comments(url, comments)
            fb = _feedback(pr, comments)
            cur["feedback"] = sorted(fb)
        now_map[url] = cur
        before = seen.get(url)
        if before:
            before = {
                **before,
                **{k: [_comment_key(i) for i in before[k]] for k in ("feedback", "arp_shown") if k in before},
            }
        if comments is not None and (before is None or "feedback" not in before):
            mark_comments_read(session_id, url)
        arp_ids = sorted(i for i in (fb or {}) if _is_arp(fb[i]))
        if before is None:
            cur["arp_reported"] = arp.get("id")
            cur["arp_shown"] = arp_ids
            continue
        arp_text = _notice_arp(arp, fb, arp_ids, before, cur, now_ts)
        if arp_text:
            events.append((url, arp_text))
        if fb and "feedback" in before:
            shown = set(cur["arp_shown"])
            new = [i for i in fb if i not in set(before["feedback"]) and not (_is_arp(fb[i]) and i in shown)]
            for i in new:
                c = fb[i]
                where = f" on {c['path']}:{c['line'] or '?'}" if c["path"] else ""
                events.append((url, f"new comment from {c['who']}{where}: {_brief(c['body'], 200)}".rstrip(": ")))
        if before.get("state") == "OPEN" and state in ("MERGED", "CLOSED"):
            events.append((url, state.lower()))
        if state == "MERGED" and "merge_checks" in before and cur["merge_checks"] != before["merge_checks"]:
            text = _ci_event(pr, cur["merge_checks"], "mergeChecks")
            if text:
                events.append((url, f"post-merge {text}"))
        if state != "OPEN":
            continue
        head_changed = bool(head and before.get("head") and head != before["head"])
        if head_changed and not pushed_recently:
            events.append((url, f"new commit {head[:10]} pushed from outside this session"))
        if cur["checks"] != before.get("checks") or head_changed:
            text = _ci_event(pr, cur["checks"])
            if text:
                events.append((url, text))
        prev_review = _LEGACY_REVIEW.get(before.get("review"), before.get("review"))
        became_ready_after_ci = (
            cur["review"] == "ready"
            and prev_review == "approved"
            and cur["checks"] == "pass"
            and before.get("checks") != "pass"
        )
        if cur["review"] != prev_review and cur["review"] in REVIEW_EVENTS and not became_ready_after_ci:
            events.append((url, REVIEW_EVENTS[cur["review"]]))
    if now_map != seen or events:
        now_ts = time.time()
        last_id = None
        with _db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if now_map != seen:
                    for url in set(seen) - set(now_map):
                        conn.execute("DELETE FROM seen WHERE session_id = ? AND url = ?", (session_id, url))
                    for url, state in now_map.items():
                        if seen.get(url) != state:
                            conn.execute(
                                "INSERT INTO seen(session_id, url, state_json) VALUES (?, ?, ?)"
                                " ON CONFLICT(session_id, url) DO UPDATE SET state_json = excluded.state_json",
                                (session_id, url, json.dumps(state)),
                            )
                for url, text in events:
                    cur = conn.execute(
                        "INSERT INTO events(ts, kind, session_id, url, text) VALUES (?, 'event', ?, ?, ?)",
                        (now_ts, session_id, url, text),
                    )
                    last_id = cur.lastrowid
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        if last_id is not None:
            _touch_notify(last_id)


def drain(session_id, consumer="agent"):
    """Read unread PR status events for (session_id, consumer) and advance its cursor."""
    if not session_id:
        return ""
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT last_event_id FROM cursors WHERE session_id = ? AND consumer = ?",
                (session_id, consumer),
            ).fetchone()
            last_id = row[0] if row else 0
            rows = conn.execute(
                "SELECT id, url, text FROM events WHERE session_id = ? AND kind = 'event' AND id > ? ORDER BY id",
                (session_id, last_id),
            ).fetchall()
            if rows:
                conn.execute(
                    "INSERT INTO cursors(session_id, consumer, last_event_id) VALUES (?, ?, ?)"
                    " ON CONFLICT(session_id, consumer) DO UPDATE SET last_event_id = excluded.last_event_id",
                    (session_id, consumer, rows[-1][0]),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    if not rows:
        return ""
    events = [f"{url}: {text}" for _, url, text in rows]
    return (
        "[argus-pr] A PR this session tracks changed status. This is an automated notice, not a message"
        ' from the user. Begin your reply with one line that starts with "PR update:" and names the'
        " PR and the change, so the user can see you are reacting to it, then handle it.\n"
        + "\n".join(f"- {e}" for e in events)
        + (
            f"\nFull comment text: python3 ~/.config/argus-pr/argus_pr.py comments {session_id}"
            ' (pi: pr_status with comments: "new"). Once a review comment is addressed and pushed, reply on its'
            " thread with what changed (or why not) and resolve it."
            if any(text.startswith("new comment") or "\n  - " in text for _, _, text in rows)
            else ""
        )
    )


def _url_number(url):
    try:
        return int((url or "").rsplit("/", 1)[-1])
    except ValueError:
        return 0


def format_countdown(seconds):
    """Compact remaining time until the next check: 18s, 4m12s, 1h05m."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def status_lines(session_id):
    """One line per PR the session tracks, from the cached status, for agents to read."""
    out = []
    for url in sorted(session_prs(session_id), key=lambda u: (repo_of(u).lower(), _url_number(u))):
        pr = url_pr(url)
        if pr is None:
            out.append(f"{url}  status not fetched yet (checking)")
            continue
        if not pr:
            out.append(f"{url}  not found")
            continue
        next_str = (
            "checking"
            if pr.get("_refreshing")
            else (
                f"next {format_countdown(pr['_next_check'] - time.time())}" if pr.get("_next_check") is not None else ""
            )
        )
        if "state" not in pr:
            parts = [url, "check error"]
            if next_str:
                parts.append(next_str)
            if pr.get("_error"):
                parts.append(f"error: {pr['_error']}")
            out.append("  ".join(parts))
            continue
        state = pr.get("state") or "?"
        if state == "OPEN" and pr.get("isDraft"):
            state = "DRAFT"
        passed, total = check_counts(pr)
        result = checks(pr) or "none"
        failed = _failed_names(pr)
        parts = [
            url,
            state,
            f"head {(pr.get('headRefOid') or '?')[:10]}",
            f"checks {result} {passed}/{total}",
        ]
        if failed:
            parts.append(f"failing: {', '.join(failed)}")
        if state in ("OPEN", "DRAFT"):
            rev = review_state(pr)
            if rev:
                parts.append(f"review {rev}")
            for note in pr.get("_notes") or []:
                if note.get("items"):
                    parts.append(f"{note.get('prefix', '')}{', '.join(note['items'])}")
                elif note.get("text"):
                    parts.append(note["text"])
        if pr.get("mergeChecks"):
            m_passed, m_total = check_counts(pr, "mergeChecks")
            parts.append(f"post-merge checks {merge_checks(pr) or 'none'} {m_passed}/{m_total}")
            m_failed = _failed_names(pr, "mergeChecks")
            if m_failed:
                parts.append(f"post-merge failing: {', '.join(m_failed)}")
        if next_str:
            parts.append(next_str)
        if pr.get("_error"):
            parts.append(f"error: {pr['_error']}")
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
        if current and (current.get("url") or current.get("_error")):
            if not current.get("url"):
                current = {**current, "branch": branch}
            out.append((current, True))
    for url in session_prs(session_id):
        if url != (current or {}).get("url"):
            data = url_pr(url)
            out.append(
                (
                    {
                        "number": url.rsplit("/", 1)[-1],
                        **(data if data is not None else {"_refreshing": True}),
                        "url": url,
                    },
                    False,
                )
            )
    return out


RESET = "\033[0m"
# Basic ANSI SGR codes (30-37 / 90-97) so colours follow the terminal theme.
MAGENTA, BLUE, CYAN, GREEN, YELLOW, RED, WHITE, DIM = 35, 34, 36, 32, 33, 31, 37, 90
BOLD = 1
CHECK_GLYPH = {"pass": (GREEN, "✓"), "fail": (RED, "✗"), "pending": (YELLOW, "…")}
REVIEW = {
    "ready": (GREEN, "ready"),
    "approved": (GREEN, "approved"),
    "changes": (RED, "changes"),
    "blocked": (RED, "blocked"),
}


def c(code, text):
    return f"\033[{code}m{text}{RESET}"


def link(url, text):
    """OSC 8 hyperlink, so the label opens the PR on click."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\" if url else text


def label(pr, prefix=""):
    """'#12 draft ✓ approved'-style label; state and review only when notable."""
    if pr.get("number") is None:
        return c(RED, "! check err") if pr.get("_error") else ""
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
        review = REVIEW.get(review_state(pr))
        if review:
            bits.append(c(*review))
    if pr.get("_error"):
        bits.append(c(RED, "!"))
    return link(pr.get("url"), " ".join(bits))


PR_COMMAND = re.compile(r"\bgh\s+pr\s+(create|ready|edit|merge)\b")
PUSH_COMMAND = re.compile(r"\bgit\b[^;&|]*\bpush\b")


_PATH = r"(\"[^\"]+\"|'[^']+'|[^\s;&|()]+)"
CD_COMMAND = re.compile(r"(?:^|[;&|(]\s*)cd\s+" + _PATH)
GIT_C_PUSH = re.compile(r"\bgit\s+-C\s+" + _PATH + r"[^;&|]*\bpush\b")


def push_dir(command, cwd):
    """The directory a git push in command ran in: its git -C, else the last cd before
    it, else cwd."""
    push = PUSH_COMMAND.search(command)
    if not push:
        return cwd
    path = None
    git_c = GIT_C_PUSH.search(command)
    if git_c and git_c.start() == push.start():
        path = git_c.group(1)
    else:
        cds = [m for m in CD_COMMAND.finditer(command) if m.end() <= push.start()]
        if cds:
            path = cds[-1].group(1)
    if not path:
        return cwd
    path = os.path.expandvars(os.path.expanduser(path.strip("\"'")))
    path = os.path.normpath(os.path.join(cwd, path))
    return path if os.path.isdir(path) else cwd


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
                    if PUSH_COMMAND.search(command) and cwd:
                        cwd = push_dir(command, cwd)
                        if cwd not in push_dirs:
                            push_dirs.append(cwd)
    for cwd in push_dirs:
        if os.path.isdir(cwd):
            with contextlib.suppress(Exception):
                resolve_branch_pr(session_id, cwd)


def agent_session_ids():
    """The calling Claude session's ID, then the sessions it was resumed or forked from
    (nearest first), read from its transcript. [] outside Claude."""
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if not session_id:
        return []
    parents = []
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    for path in glob.glob(os.path.join(config, "projects", "*", session_id + ".jsonl")):
        with contextlib.suppress(OSError), open(path) as f:
            for sid in re.findall(r'"session_?[iI]d":"([0-9a-f-]{36})"', f.read()):
                if sid != session_id and sid not in parents:
                    parents.append(sid)
    return [session_id, *reversed(parents)]


def resolve_branch_pr(session_id, cwd):
    """Record the current branch's PR in cwd, if it has one (runs detached)."""
    out = _run_gh(["pr", "view", "--json", "url", "-q", ".url"], cwd=cwd)
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
