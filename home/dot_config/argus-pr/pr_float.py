# Managed by chezmoi — source: home/dot_config/argus-pr/pr_float.py
# Session PR tracker as a vertical tiled Rex pane on the right of the coding
# agent's pane. Agent-neutral: adapters (see argus_pr.py) supply the session ID,
# the working directory and, when known, the agent's pid.
#
#   ensure <session_id> <cwd> <pid>  (SessionStart hook) record the session for
#                                    this Rex block, start a waiter if nothing
#                                    is running for it, and prune the state of
#                                    closed panes
#   wait <agent_block>              detached: open the pane once the agent's
#                                    pane is tiled in an unzoomed window; exit,
#                                    removing the pane's state, if Rex no longer
#                                    has the pane or its session
#   watch <agent_block>             the pane's own program: draw the PRs (or a
#                                    short message when there are none) sized to
#                                    the terminal; if the agent pane leaves its
#                                    window's layout it hands back to a waiter
#                                    and closes. Also queues PR notifications
#                                    for the agent (pr_tracking.notice_changes)
#
# One of wait or watch runs per Rex block, its pid in the block's state file;
# either exits when the agent does. Both re-exec themselves, keeping their pid
# and the pane, when pr_float.py or pr_tracking.py changes on disk.
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import termios
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_tracking  # noqa: E402

TICK = 2
# A waiter only needs to notice the first PR; nothing is on screen to keep fresh.
WAIT_TICK = 5
# How long git facts are reused between ticks.
GIT_TTL = 10
# Width sizing for the right-hand tiled pane: horizontal chrome cells, fallback
# total columns before a client reports size, and min/max share of the split.
CHROME_COLS = 3
FALLBACK_COLS = 160
MIN_SHARE = 0.05
MAX_SHARE = 0.30
# How long a waiter that opened the pane waits for it to take over.
HANDOFF = 15
# Shown in the pane's label so one still running older code is easy to spot.
# Bump it whenever pr_float.py or pr_tracking.py changes behaviour.
VERSION = 31
LABEL = f"👁 Argus v{VERSION}"
SUBLINE_MAX = 48
# The code a running wait or watch reloads when it changes on disk.
CODE = (os.path.abspath(__file__), os.path.abspath(pr_tracking.__file__))


def _code_files():
    return (*CODE, *pr_tracking.plugin_files())


def _code_signature():
    sig = []
    for path in _code_files():
        try:
            st = os.stat(path)
            sig.append((path, st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append((path, None))
    return sig


class Reloader:
    """Tells a long-running wait or watch when to re-exec itself with new code.

    A change must look the same on two consecutive checks, so a file still being
    written is not loaded, and the new code must compile; code that does not is
    skipped until the files change again.
    """

    def __init__(self):
        self.loaded = self.last = _code_signature()

    def due(self):
        sig = _code_signature()
        settled, self.last = sig == self.last, sig
        if sig == self.loaded or not settled:
            return False
        try:
            for path in _code_files():
                with open(path) as f:
                    compile(f.read(), path, "exec")
        except Exception:
            self.loaded = sig
            return False
        return True


def _reexec(mode, agent_block):
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), mode, agent_block])


def _state_path(block):
    return pr_tracking._path("float", re.sub(r"[^\w.-]", "_", block) + ".json")


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def ancestor_pid(*names):
    """The nearest ancestor process whose command is one of names, if any."""
    pid = os.getppid()
    for _ in range(10):
        out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True)
        fields = out.stdout.split(None, 1)
        if len(fields) < 2:
            return None
        if os.path.basename(fields[1].strip()) in names:
            return pid
        pid = int(fields[0])
        if pid <= 1:
            return None
    return None


def _state(block):
    return pr_tracking._read_json(_state_path(block)) or {}


def _claim(block, mode):
    """Make this process the one running for block."""
    state = _state(block)
    state.update(watcher_pid=os.getpid(), mode=mode)
    pr_tracking._write_json(_state_path(block), state)


def _mine(state):
    if state.get("watcher_pid") != os.getpid():
        return False
    return not state.get("agent_pid") or _alive(state["agent_pid"])


def running(block):
    """Whether the box is showing PRs for this Rex block."""
    state = _state(block)
    return state.get("mode") == "watch" and _alive(state.get("watcher_pid"))


def rex(method, args, session=None):
    out = subprocess.run(
        ["rex", "api", "call", "-s", session or os.environ.get("REX_SESSION", ""), method, json.dumps(args)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"rex {method} failed")
    return json.loads(out.stdout or "{}")


def block_cols(block):
    """Current terminal columns of block, or None if Rex has not measured it."""
    out = subprocess.run(
        ["rex", "block", "call", "-s", os.environ.get("REX_SESSION", ""), "-b", block, "size", "{}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    data = json.loads(out.stdout) if out.returncode == 0 else {}
    cols = data.get("columns")
    return cols if isinstance(cols, int) and cols > 0 else None


def _find(layout, block):
    """The rect of block in a layout tree."""
    if not isinstance(layout, dict):
        return None
    if layout.get("block_id") == block:
        return layout.get("rect")
    for child in layout.values():
        found = _find(child, block) if isinstance(child, dict) else None
        if found:
            return found
    return None


def locate(view, block):
    """(window_id, tiled rect of block, layer holding block, window is zoomed)."""
    for window in view.get("windows") or []:
        for layer in window.get("layers") or []:
            ids = {b.get("block_id") for b in layer.get("blocks") or []}
            if block in ids:
                rect = _find(layer.get("layout"), block) if layer.get("kind") == "tiled" else None
                return window.get("window_id"), rect, layer, bool(window.get("zoomed_block_id"))
    return None, None, None, False


_cache = {}


def _cached(key, ttl, fn, ok=bool):
    """fn()'s result, reused for ttl seconds; failed results (per ok) are not kept."""
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = fn()
    if ok(value):
        _cache[key] = (now, value)
    return value


def session_prs(state):
    """([(pr, is_current_branch)], name of the repo the agent is in)."""
    session_id, cwd = state.get("session_id"), state.get("cwd") or os.path.expanduser("~")
    common = _cached(
        ("common", cwd),
        GIT_TTL,
        lambda: pr_tracking.git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"),
    )
    branch = _cached(("branch", cwd), GIT_TTL, lambda: pr_tracking.git(cwd, "branch", "--show-current"))
    here = os.path.basename(os.path.dirname(common)) if common else ""
    return pr_tracking.prs(session_id, cwd, common, branch), here


def _pr_number(pr):
    try:
        return int(pr.get("number") or 0)
    except (TypeError, ValueError):
        return 0


def lines(found, here, max_rows=None):
    t = pr_tracking
    if not found:
        return [" " + t.c(t.DIM, "No PRs yet")]
    groups = {}
    for pr, current in found:
        repo = t.repo_of(pr.get("url"))
        groups.setdefault(repo, []).append((pr, current))
    ordered_repos = sorted(groups, key=lambda r: (r != here, r.lower()))
    for repo in ordered_repos:
        groups[repo].sort(key=lambda item: _pr_number(item[0]))
    mark = {True: t.c(t.GREEN, "⎇ "), False: "  "}
    compact = max_rows is not None and max_rows <= 2
    if compact:
        body = []
        for repo in ordered_repos:
            prefix = "" if repo == here else repo
            for pr, current in groups[repo]:
                pr_cell, ci, review, nxt = cells(pr, prefix)
                body.append([mark[current] + pr_cell, ci, review, nxt])
        widths = [max(visible(row[i]) for row in body) for i in range(4)]
        return [" " + "  ".join(pad(col, w) for col, w in zip(cols, widths, strict=True)) for cols in body]
    header = [t.c(t.BOLD, "PR"), t.c(t.BOLD, "CI"), t.c(t.BOLD, "Review"), t.c(t.BOLD, "Next")]
    grouped_rows = []
    all_rows = [header]
    for repo in ordered_repos:
        rows = []
        for pr, current in groups[repo]:
            pr_cell, ci, review, nxt = cells(pr, "")
            row = [mark[current] + pr_cell, ci, review, nxt]
            rows.append((row, pr))
            all_rows.append(row)
        grouped_rows.append((repo, rows))
    widths = [max(visible(row[i]) for row in all_rows) for i in range(4)]

    def fmt(cols):
        return " " + "  ".join(pad(col, w) for col, w in zip(cols, widths, strict=True))

    out = [fmt(header)]
    for repo, rows in grouped_rows:
        if repo:
            out.append(" " + t.c(t.CYAN, repo))
        for row, pr in rows:
            out.append(fmt(row))
            out.extend(_sublines(pr))
    return out


def _trunc(text, limit=SUBLINE_MAX):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _sublines(pr):
    t = pr_tracking
    colors = {"yellow": t.YELLOW, "red": t.RED, "dim": t.DIM, "green": t.GREEN, "cyan": t.CYAN}
    out = []
    if pr.get("state") == "OPEN":
        for note in pr.get("_notes") or []:
            color = colors.get(note.get("color"), t.YELLOW)
            items = note.get("items") or []
            if items:
                prefix = note.get("prefix") or ""
                joined = ", ".join(items)
                if len(prefix) + len(joined) <= SUBLINE_MAX:
                    out.append("   " + t.c(color, prefix + joined))
                else:
                    indent = " " * len(prefix)
                    for i, item in enumerate(items):
                        out.append("   " + t.c(color, (prefix if i == 0 else indent) + _trunc(item)))
            elif note.get("text"):
                out.append("   " + t.c(color, _trunc(note["text"])))
    err = pr.get("_error")
    if err:
        out.append("   " + t.c(t.RED, f"! {_trunc(err)}"))
    return out


def _next_cell(pr):
    t = pr_tracking
    if pr.get("_refreshing"):
        return t.c(t.YELLOW, "…")
    next_at = pr.get("_next_check")
    if next_at is not None:
        countdown = t.format_countdown(next_at - time.time())
        return t.c(t.RED, f"! {countdown}") if pr.get("_error") else t.c(t.DIM, countdown)
    return t.c(t.RED, "!") if pr.get("_error") else t.c(t.DIM, "–")


def cells(pr, prefix):
    """(PR, CI, Review, Next) cells for one PR."""
    t = pr_tracking
    nxt = _next_cell(pr)
    number = pr.get("number")
    name = t.c(t.GREEN, f"{prefix}#{number}") if number is not None else t.c(t.DIM, pr.get("branch") or "branch")
    state = pr.get("state")
    if state in ("MERGED", "CLOSED"):
        tag = t.c(t.MAGENTA, "merged") if state == "MERGED" else t.c(t.RED, "closed")
        return t.link(pr.get("url"), f"{name} {tag}"), t.c(t.DIM, "–"), t.c(t.DIM, "–"), nxt
    if pr.get("isDraft"):
        name += " " + t.c(t.DIM, "draft")
    if pr.get("mergeable") == "CONFLICTING":
        name += " " + t.c(t.RED, "conflict")
    status = t.checks(pr)
    if status:
        color, glyph = t.CHECK_GLYPH[status]
        passed, total = t.check_counts(pr)
        ci = t.c(color, f"{glyph} {passed}/{total}")
    elif not state and pr.get("_error"):
        ci = t.c(t.RED, "err")
    else:
        ci = t.c(t.DIM, "–")
    rev = t.review_state(pr)
    review = t.REVIEW.get(rev) or ((t.YELLOW, rev) if rev else (t.DIM, "–"))
    return t.link(pr.get("url"), name), ci, t.c(*review), nxt


ANSI = re.compile(r"\033\[[\d;]*m|\033\]8;;.*?\033\\")


def visible(text):
    return len(ANSI.sub("", text))


def pad(text, width):
    return text + " " * (width - visible(text))


def want_cols(body):
    """Usable columns needed to show every line in body without clipping."""
    return max((visible(line) for line in body), default=0) + 1


def split_ratio(agent_block, body):
    """Ratio for the before (agent) side of a horizontal split putting PR Box on the right."""
    total = block_cols(agent_block) or FALLBACK_COLS
    share = min(max((want_cols(body) + CHROME_COLS) / total, MIN_SHARE), MAX_SHARE)
    return round(1 - share, 4)


def _contains(node, block):
    if not isinstance(node, dict):
        return False
    if node.get("block_id") == block:
        return True
    split = node.get("split")
    return isinstance(split, dict) and (_contains(split.get("before"), block) or _contains(split.get("after"), block))


def _enclosing_split(node, before_block, after_block, direction="horizontal"):
    """Innermost split of direction with before_block in before and after_block in after."""
    if not isinstance(node, dict):
        return None
    split = node.get("split")
    if not isinstance(split, dict):
        return None
    for side in ("before", "after"):
        deeper = _enclosing_split(split.get(side), before_block, after_block, direction)
        if deeper:
            return deeper
    if (
        split.get("direction") == direction
        and _contains(split.get("before"), before_block)
        and _contains(split.get("after"), after_block)
    ):
        return split
    return None


def enforce_width(layer, agent_block, me, body, have_cols, sizing):
    """Keep the tiled PR pane at the width needed to show every line in full."""
    if not have_cols or have_cols <= 0:
        return
    layout = layer.get("layout")
    split = _enclosing_split(layout, agent_block, me)
    if split:
        before_id, after_id, on_right = agent_block, me, True
    else:
        split = _enclosing_split(layout, me, agent_block)
        if not split:
            return
        before_id, after_id, on_right = me, agent_block, False
    cur_ratio = split.get("ratio")
    if not isinstance(cur_ratio, int | float) or not (0 < cur_ratio < 1):
        return
    cur_share = (1 - cur_ratio) if on_right else cur_ratio
    want = want_cols(body)
    # Until a client re-measures the PTY after our last resize, have_cols still
    # reflects the old ratio; reuse the last settled split_cols instead.
    stale = (
        sizing.get("ratio") is not None and abs(cur_ratio - sizing["ratio"]) < 0.001 and have_cols == sizing.get("cols")
    )
    sibling = split.get("before" if on_right else "after") or {}
    if sibling.get("block_id") == agent_block:
        other_cols = block_cols(agent_block)
        if other_cols:
            sizing["split_cols"] = other_cols + have_cols + CHROME_COLS
    if not stale:
        if "split_cols" not in sizing or sibling.get("block_id") != agent_block:
            sizing["split_cols"] = (have_cols + CHROME_COLS) / cur_share
        sizing["ratio"] = None
        if want <= have_cols <= want + 1:
            return
    split_cols = sizing.get("split_cols")
    if not split_cols:
        return
    target_share = min(max((want + CHROME_COLS) / split_cols, MIN_SHARE), MAX_SHARE)
    target_ratio = round((1 - target_share) if on_right else target_share, 4)
    if abs(target_ratio - cur_ratio) < 0.003:
        return
    rex(
        "session.resize_pane",
        {
            "direction": "horizontal",
            "before_block_id": before_id,
            "after_block_id": after_id,
            "ratio": target_ratio,
        },
    )
    sizing["ratio"], sizing["cols"] = target_ratio, have_cols


def _spawn(mode, agent_block):
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), mode, agent_block],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def ensure(session_id, cwd, pid=""):
    block = os.environ.get("REX_BLOCK")
    if not block or not os.environ.get("REX_SESSION") or not shutil.which("rex"):
        return
    state = _state(block)
    state.update(session_id=session_id, cwd=cwd, agent_pid=int(pid) if pid else None)
    pr_tracking._write_json(_state_path(block), state)
    if not _alive(state.get("watcher_pid")):
        _spawn("wait", block)
    prune()


def live_blocks(complete=False):
    """{block_id: Rex session_id} for every block on the Rex server, detached ones
    included. With complete, raise rather than leave out a session Rex did not list."""
    out = subprocess.run(["rex", "session", "list", "--json"], capture_output=True, text=True, timeout=10)
    if complete and out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "rex session list failed")
    found = {}
    for session in json.loads(out.stdout or "{}").get("sessions") or []:
        sid = session.get("session_id")
        try:
            for block in rex("session.list_blocks", {}, sid).get("blocks") or []:
                found[block["block_id"]] = sid
        except Exception:
            if complete:
                raise
    return found


def prune():
    """Remove the state of panes Rex no longer has whose box or waiter has exited.

    Only after a complete listing of Rex's blocks, so a failed call never removes
    a live pane's state.
    """
    try:
        live = live_blocks(complete=True)
    except Exception:
        return
    directory = os.path.dirname(_state_path("x"))
    with contextlib.suppress(OSError):
        for name in os.listdir(directory):
            block = name.removesuffix(".json").replace("block_", "block:", 1)
            if not name.endswith(".json") or block in live or _alive(_state(block).get("watcher_pid")):
                continue
            with contextlib.suppress(OSError):
                os.remove(os.path.join(directory, name))


def _lineage_block(session_ids, live):
    """The live block whose box state belongs to one of session_ids, preferring the
    earliest of session_ids (the agent's own session) and then the newest state."""
    directory = os.path.dirname(_state_path("x"))
    best = None
    with contextlib.suppress(OSError):
        for name in os.listdir(directory):
            block = name.removesuffix(".json").replace("block_", "block:", 1)
            if not name.endswith(".json") or block not in live:
                continue
            sid = _state(block).get("session_id")
            if sid not in session_ids:
                continue
            rank = (-session_ids.index(sid), os.path.getmtime(os.path.join(directory, name)))
            if best is None or rank > best[0]:
                best = (rank, block)
    return best[1] if best else None


def reopen(session_ids=()):
    """Open the agent's box (the /argus-pr command). An open box is closed first and
    opened fresh.

    The pane is REX_BLOCK when Rex still has it. A resumed or forked agent can carry
    the REX_BLOCK of a pane that no longer exists, so otherwise it is the live pane
    whose box belongs to one of session_ids: the agent's session, then the sessions
    it was forked from. The box then tracks session_ids[0], when given.
    """
    session_ids = list(session_ids)
    live = live_blocks()
    block = os.environ.get("REX_BLOCK")
    if block not in live or not _state(block).get("session_id"):
        block = _lineage_block(session_ids, live)
    state = _state(block) if block else {}
    if not state.get("session_id"):
        print("No PR box state for this pane: not running in Rex, or the session hasn't started.")
        return
    os.environ.update(REX_BLOCK=block, REX_SESSION=live[block])
    if running(block):
        # SIGHUP makes watch exit through its cleanup, which closes the layer.
        pid = state["watcher_pid"]
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGHUP)
        deadline = time.time() + 5
        while _alive(pid) and time.time() < deadline:
            time.sleep(0.1)
        if _alive(pid):
            print("Could not close the open PR box.")
            return
    session_id = session_ids[0] if session_ids else state["session_id"]
    ensure(session_id, state.get("cwd") or os.getcwd(), state.get("agent_pid") or "")
    print("Reopening the PR box.")


def _block_gone(block):
    """Whether Rex no longer has block or its session. Other errors reaching Rex are
    not taken to mean the block is gone. A detached block still exists."""
    try:
        rex("session.describe_block", {"block_id": block})
    except RuntimeError as e:
        return "not found" in str(e)
    except Exception:
        return False
    return False


def wait(agent_block):
    _claim(agent_block, "wait")
    reloader = Reloader()
    gone = 0
    while True:
        if reloader.due():
            _reexec("wait", agent_block)
        state = _state(agent_block)
        if not _mine(state):
            return
        # The pane was closed: nothing will show it again, so stop waiting. Two
        # ticks in a row, so one failed call to Rex does not end the waiter.
        gone = gone + 1 if _block_gone(agent_block) else 0
        if gone >= 2:
            # Block IDs are never reused, so the pane's state is of no further use.
            with contextlib.suppress(OSError):
                os.remove(_state_path(agent_block))
            return
        # Wait while the agent's pane is not tiled (floated, detached, or
        # between windows) or the window is zoomed (splitting would unzoom it).
        _, rect, _, zoomed = locate(rex("session.view", {}), agent_block)
        if rect and not zoomed:
            ratio = split_ratio(agent_block, lines(*session_prs(state)))
            break
        time.sleep(WAIT_TICK)
    rex(
        "session.new_split",
        {
            "anchor_id": agent_block,
            "direction": "horizontal",
            "side": "after",
            "ratio": ratio,
            "focus": False,
            "layout": {
                "block": {
                    "flavor": "com.superlogical.terminal.shell",
                    "label": LABEL,
                    "options": {
                        "command": [sys.executable, os.path.abspath(__file__), "watch", agent_block],
                        "exit": {"on_completion": True},
                    },
                }
            },
        },
    )
    # Stay the block's owner until the pane starts, so a SessionStart in the
    # meantime does not start a second waiter.
    for _ in range(HANDOFF):
        if _state(agent_block).get("watcher_pid") != os.getpid():
            return
        time.sleep(1)


def draw(body):
    """Paint body in place: each row at an absolute position, clipped to the pane.

    Nothing is ever written below the last row or past the last column, so the
    terminal has nothing to scroll or wrap, and rows are overwritten rather than
    cleared first, so redraws do not flicker.
    """
    size = shutil.get_terminal_size()
    rows = body[: size.lines]
    # Clear the row before writing it: with wrap off the cursor stays on the
    # last column, so erasing to end of line afterwards would eat the last cell.
    out = "".join(f"\033[{i};1H\033[2K{row}" for i, row in enumerate(rows, 1))
    if len(rows) < size.lines:
        out += f"\033[{len(rows) + 1};1H\033[J"
    sys.stdout.write(out)
    sys.stdout.flush()


def mute_input():
    """Stop the terminal echoing typed keys into the pane; returns the old settings.

    Ctrl-C still works, and closes the pane.
    """
    try:
        saved = termios.tcgetattr(sys.stdin)
        muted = termios.tcgetattr(sys.stdin)
        muted[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, muted)
        return saved
    except Exception:
        return None


def discard_input():
    with contextlib.suppress(Exception):
        termios.tcflush(sys.stdin, termios.TCIFLUSH)


def _close_self(block):
    _, _, layer, _ = locate(rex("session.view", {}), block)
    if not layer:
        return
    if layer.get("kind") == "floating":
        rex("session.close_layer", {"layer_id": layer["layer_id"]})
    else:
        rex("block.close", {"block_id": block, "keep_last": True})


def watch(agent_block):
    me = os.environ.get("REX_BLOCK", "")
    _claim(agent_block, "watch")
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(0))
    reloader, reloading = Reloader(), False
    # The pane's label is set when it opens; after a reload it names the old version.
    with contextlib.suppress(Exception):
        subprocess.run(
            ["rex", "block", "rename", "-s", os.environ.get("REX_SESSION", ""), me, LABEL],
            capture_output=True,
            timeout=10,
        )
    # Alternate screen (no scrollback), no line wrap, no wheel-to-arrow-keys, no cursor.
    sys.stdout.write("\033[?1049h\033[?7l\033[?1007l\033[?25l")
    saved = mute_input()
    sizing = {}
    last_sid = None
    try:
        while True:
            state = _state(agent_block)
            if not _mine(state):
                return
            sid = state.get("session_id")
            if sid != last_sid:
                _cache.clear()
                last_sid = sid
            view = rex("session.view", {})
            agent_window, rect, _, zoomed = locate(view, agent_block)
            my_window, _, layer, _ = locate(view, me)
            if not layer:
                return
            # The agent's pane left this window or its layout, or this watcher
            # reloaded inside an older floating layer: hand back to a waiter to
            # open a tiled pane beside the agent.
            if layer.get("kind") != "tiled" or not rect or agent_window != my_window:
                _spawn("wait", agent_block)
                return
            found, here = session_prs(state)
            with contextlib.suppress(Exception):
                pr_tracking.notice_changes(state.get("session_id"), [pr for pr, _ in found])
            size = shutil.get_terminal_size()
            body = lines(found, here, max_rows=size.lines)
            me_block = next((b for b in layer.get("blocks") or [] if b.get("block_id") == me), None)
            # Before a client owns and measures the pane, Rex reports a fallback 80-col PTY.
            if not zoomed and me_block and me_block.get("owner") and view.get("active_window_id") in (None, my_window):
                with contextlib.suppress(Exception):
                    enforce_width(layer, agent_block, me, body, size.columns, sizing)
            draw(body)
            time.sleep(TICK)
            discard_input()
            if reloader.due():
                reloading = True
                break
    finally:
        with contextlib.suppress(Exception):
            sys.stdout.write("\033[?1049l\033[?7h\033[?25h")
            sys.stdout.flush()
        with contextlib.suppress(Exception):
            if saved:
                termios.tcsetattr(sys.stdin, termios.TCSANOW, saved)
        if not reloading:
            with contextlib.suppress(Exception):
                _close_self(me)
    if reloading:
        _reexec("watch", agent_block)


if __name__ == "__main__":
    mode, args = sys.argv[1:2], sys.argv[2:]
    with contextlib.suppress(Exception):
        if mode == ["ensure"]:
            ensure(*args[:3])
        elif mode == ["reopen"]:
            reopen()
        elif mode == ["wait"]:
            wait(args[0])
    if mode == ["watch"]:
        watch(args[0])
