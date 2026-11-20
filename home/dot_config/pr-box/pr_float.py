# Managed by chezmoi — source: home/dot_config/pr-box/pr_float.py
# Session PR tracker as a Rex floating box at the top right of the coding
# agent's pane. Agent-neutral: adapters (see pr_box.py) supply the session ID, the
# working directory and, when known, the agent's pid.
#
#   ensure <session_id> <cwd> <pid>  (SessionStart hook) record the session for
#                                    this Rex block and start a waiter if
#                                    nothing is running for it
#   wait <agent_block>              detached: open the box once the agent's
#                                    pane is tiled in a window
#   watch <agent_block>             the box's own program: draw the PRs (or a
#                                    short message when there are none) and keep
#                                    the box sized to fit at the top right of
#                                    the agent's pane; if the pane leaves its
#                                    window's layout it hands back to a waiter
#                                    and closes. It also queues PR notifications
#                                    for the agent (pr_tracking.notice_changes)
#
# One of wait or watch runs per Rex block, its pid in the block's state file;
# either exits when Claude does. Both re-exec themselves, keeping their pid and
# the box's layer, when pr_float.py or pr_tracking.py changes on disk. The box is a Rex floating layer sized in
# fractions of the window, so its size is recomputed from the window's cell
# size on every tick.
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
# How long git facts and the agent pane's size are reused between ticks.
GIT_TTL = 10
SIZE_TTL = 6
# Cells the floating layer's frame takes, until measured, and the most it can be.
FRAME = (3, 3)
FRAME_MAX = (8, 6)
# How long a waiter that opened the box waits for the box to take over.
HANDOFF = 15
# Shown in the box's title so a box still running older code is easy to spot.
# Bump it whenever pr_float.py or pr_tracking.py changes behaviour.
VERSION = 6
# The code a running wait or watch reloads when it changes on disk.
CODE = (os.path.abspath(__file__), os.path.abspath(pr_tracking.__file__))


def _code_signature():
    sig = []
    for path in CODE:
        try:
            st = os.stat(path)
            sig.append((st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append(None)
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
            for path in CODE:
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


def block_size(block):
    return block_report(block)[:2]


def block_report(block):
    """(columns, rows, when a client last reported that size)."""
    out = subprocess.run(
        ["rex", "block", "call", "-s", os.environ.get("REX_SESSION", ""), "-b", block, "size", "{}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    data = json.loads(out.stdout) if out.returncode == 0 else {}
    stamp = max((d.get("updated_at") or "" for d in data.get("desired") or []), default="")
    return data.get("columns"), data.get("rows"), stamp


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
    """(window_id, tiled rect of block, layer holding block)."""
    for window in view.get("windows") or []:
        for layer in window.get("layers") or []:
            ids = {b.get("block_id") for b in layer.get("blocks") or []}
            if block in ids:
                rect = _find(layer.get("layout"), block) if layer.get("kind") == "tiled" else None
                return window.get("window_id"), rect, layer
    return None, None, None


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


def lines(found, here):
    rows = []
    for pr, current in found:
        repo = pr_tracking.repo_of(pr.get("url"))
        prefix = "" if repo == here else repo
        rows.append((current, *cells(pr, prefix)))
    t = pr_tracking
    if not rows:
        message = "No PRs yet"
        return [
            t.c(t.DIM, "┌" + "─" * (len(message) + 2) + "┐"),
            t.c(t.DIM, "│") + " " + t.c(t.DIM, message) + " " + t.c(t.DIM, "│"),
            t.c(t.DIM, "└" + "─" * (len(message) + 2) + "┘"),
        ]
    mark = {True: t.c(t.GREEN, "⎇ "), False: "  "}
    header = [t.c(t.BOLD, "PR"), t.c(t.BOLD, "CI"), t.c(t.BOLD, "Review")]
    body = [[mark[current] + pr_cell, ci, review] for current, pr_cell, ci, review in rows]
    widths = [max(visible(row[i]) for row in [header, *body]) for i in range(3)]
    border = lambda left, mid, right: t.c(t.DIM, left + mid.join("─" * (w + 2) for w in widths) + right)  # noqa: E731
    bar = t.c(t.DIM, "│")

    def row(cols):
        return bar + bar.join(" " + pad(col, w) + " " for col, w in zip(cols, widths, strict=True)) + bar

    out = [border("┌", "┬", "┐"), row(header), border("├", "┼", "┤")]
    out += [row(cols) for cols in body]
    out.append(border("└", "┴", "┘"))
    return out


def cells(pr, prefix):
    """(PR, CI, Review) cells for one PR."""
    t = pr_tracking
    name = t.c(t.GREEN, f"{prefix}#{pr.get('number')}")
    state = pr.get("state")
    if state in ("MERGED", "CLOSED"):
        tag = t.c(t.MAGENTA, "merged") if state == "MERGED" else t.c(t.RED, "closed")
        return t.link(pr.get("url"), f"{name} {tag}"), t.c(t.DIM, "–"), t.c(t.DIM, "–")
    if pr.get("isDraft"):
        name += " " + t.c(t.DIM, "draft")
    status = t.checks(pr)
    if status:
        color, glyph = t.CHECK_GLYPH[status]
        passed, total = t.check_counts(pr)
        ci = t.c(color, f"{glyph} {passed}/{total}")
    else:
        ci = t.c(t.DIM, "–")
    decision = pr.get("reviewDecision")
    review = t.REVIEW.get(decision) or ((t.YELLOW, "needed") if decision else (t.DIM, "–"))
    return t.link(pr.get("url"), name), ci, t.c(*review)


ANSI = re.compile(r"\033\[[\d;]*m|\033\]8;;.*?\033\\")


def visible(text):
    return len(ANSI.sub("", text))


def pad(text, width):
    return text + " " * (width - visible(text))


def bounds(agent_block, rect, body, frame, stable=True):
    """[x, y, w, h] for a box holding body at the top right of rect, or None.

    The agent pane's size is cached per rect. Right after a split the pane's
    size can still be the old one, so it is only cached once rect is stable.
    """
    cols, rows = _cached(
        ("size", agent_block, tuple(rect)),
        SIZE_TTL,
        lambda: block_size(agent_block),
        ok=lambda v: stable and all(v),
    )
    if not cols or not rows:
        return None
    x, y, w, h = rect
    win_cols, win_rows = cols / w, rows / h
    want = (max(len(ANSI.sub("", line)) for line in body) + frame[0], len(body) + frame[1])
    bw, bh = min(want[0] / win_cols, w), min(want[1] / win_rows, h)
    return [round(x + w - bw, 4), round(y, 4), round(bw, 4), round(bh, 4)], (win_cols, win_rows)


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


def live_blocks():
    """{block_id: Rex session_id} for every block on the Rex server."""
    out = subprocess.run(["rex", "session", "list", "--json"], capture_output=True, text=True, timeout=10)
    found = {}
    for session in json.loads(out.stdout or "{}").get("sessions") or []:
        sid = session.get("session_id")
        with contextlib.suppress(Exception):
            for block in set(re.findall(r"block:[0-9a-f-]{36}", json.dumps(rex("session.view", {}, sid)))):
                found[block] = sid
    return found


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
    """Open the agent's box (the /pr-box command). An open box is closed first and
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


def wait(agent_block):
    _claim(agent_block, "wait")
    reloader = Reloader()
    while True:
        if reloader.due():
            _reexec("wait", agent_block)
        state = _state(agent_block)
        if not _mine(state):
            return
        # Wait while the agent's pane is not tiled (floated, detached, or
        # between windows); the box opens once it is back in a layout.
        window, rect, _ = locate(rex("session.view", {}), agent_block)
        if rect:
            placed = bounds(agent_block, rect, lines(*session_prs(state)), FRAME)
            if placed:
                break
        time.sleep(WAIT_TICK)
    rex(
        "session.new_layer",
        {
            "window_id": window,
            "bounds": placed[0],
            "layout": {
                "block": {
                    "flavor": "com.superlogical.terminal.shell",
                    "label": f"PR Box v{VERSION}",
                    "options": {
                        "command": [sys.executable, os.path.abspath(__file__), "watch", agent_block],
                        "exit": {"on_completion": True},
                    },
                }
            },
            "focus": False,
        },
    )
    # Stay the block's owner until the box starts, so a SessionStart in the
    # meantime does not start a second waiter.
    for _ in range(HANDOFF):
        if _state(agent_block).get("watcher_pid") != os.getpid():
            return
        time.sleep(1)


def settled_size(block, before, timeout=1.0):
    """The block's size once a client has drawn it after a resize, or None.

    before is the block's report from just before the resize. Until a client
    reports the new size (none does while the session is not on screen), Rex
    returns the old one, which must not be taken as the result.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        cols, rows, stamp = block_report(block)
        if cols and rows and stamp and stamp != before[2]:
            return cols, rows
        time.sleep(0.05)
    return None


def displaced(actual, target, win):
    """Whether a layer's bounds are more than half a cell away from target."""
    if not actual or len(actual) != 4:
        return True
    scale = (win[0], win[1], win[0], win[1])
    return any(abs(a - b) * n > 0.5 for a, b, n in zip(actual, target, scale, strict=True))


def draw(body):
    """Paint body in place: each row at an absolute position, clipped to the box.

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
    """Stop the terminal echoing typed keys into the box; returns the old settings.

    Ctrl-C still works, and closes the box.
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


def watch(agent_block):
    me = os.environ.get("REX_BLOCK", "")
    _claim(agent_block, "watch")
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(0))
    reloader, reloading = Reloader(), False
    # The layer's label is set when it opens; after a reload it names the old version.
    with contextlib.suppress(Exception):
        subprocess.run(
            ["rex", "block", "rename", "-s", os.environ.get("REX_SESSION", ""), me, f"PR Box v{VERSION}"],
            capture_output=True,
            timeout=10,
        )
    # Alternate screen (no scrollback), no line wrap, no wheel-to-arrow-keys, no cursor.
    sys.stdout.write("\033[?1049h\033[?7l\033[?1007l\033[?25l")
    saved = mute_input()
    frame = list(FRAME)
    placed, measured = None, False
    last_rect = None
    try:
        while True:
            state = _state(agent_block)
            if not _mine(state):
                return
            view = rex("session.view", {})
            agent_window, rect, _ = locate(view, agent_block)
            my_window, _, layer = locate(view, me)
            if not layer:
                return
            # The agent's pane left this window or its layout: a waiter
            # reopens the box beside it once it is tiled again.
            if not rect or agent_window != my_window:
                _spawn("wait", agent_block)
                return
            found, here = session_prs(state)
            with contextlib.suppress(Exception):
                pr_tracking.notice_changes(state.get("session_id"), [pr for pr, _ in found])
            body = lines(found, here)
            inner = (max(visible(line) for line in body), len(body))
            # When the box is shrinking, the new content already fits it, so
            # paint it before the resize rather than squeezing the old rows.
            current = shutil.get_terminal_size()
            if inner[0] <= current.columns and inner[1] <= current.lines:
                draw(body)
            # Pane sizes in a window that is not on screen are stale, so the
            # box is only placed while its window is the active one.
            visible_now = view.get("active_window_id") in (None, my_window)
            stable, last_rect = rect == last_rect, rect
            # Rex cannot pin a floating layer to a pane, so the box follows the
            # agent's pane on every tick: after a split, a resized window, or a
            # move or resize by hand. Everything settles within this tick, and
            # the content is drawn only once the box is its final size, so
            # there is no intermediate cut-off frame.
            actual = layer.get("bounds")
            for _ in range(3 if visible_now else 0):
                fit = bounds(agent_block, rect, body, frame, stable)
                if not fit:
                    break
                target, win = fit
                # Compare in whole cells so fraction rounding never triggers a resize.
                key = (round(target[2] * win[0]), round(target[3] * win[1]), round(win[0]), round(win[1]))
                if key == placed and not displaced(actual, target, win):
                    break
                before = block_report(me)
                rex("session.resize_layer", {"layer_id": layer["layer_id"], "bounds": target})
                actual, placed = target, key
                have = settled_size(me, before)
                if not have:
                    break
                # Measure the frame once, then only grow it if content stops
                # fitting. Re-deriving it on every resize makes the box flip
                # between sizes a cell apart.
                if not measured:
                    frame = [key[0] - have[0], key[1] - have[1]]
                    measured = True
                elif have[0] < inner[0] or have[1] < inner[1]:
                    frame = [frame[0] + max(inner[0] - have[0], 0), frame[1] + max(inner[1] - have[1], 0)]
                else:
                    break
                frame = [min(max(f, 0), m) for f, m in zip(frame, FRAME_MAX, strict=True)]
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
                _, _, layer = locate(rex("session.view", {}), me)
                if layer:
                    rex("session.close_layer", {"layer_id": layer["layer_id"]})
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
