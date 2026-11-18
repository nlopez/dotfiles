# Managed by chezmoi — source: home/dot_config/claude/pr_float.py
# Session PR tracker as a Rex floating box at the top right of Claude's pane.
#
#   ensure <session_id> <cwd> <pid>  (SessionStart hook) record the session for
#                                    this Rex block and start a waiter if
#                                    nothing is running for it
#   wait <claude_block>              detached: open the box once there is a PR
#   watch <claude_block>             the box's own program: draw the PRs and
#                                    resize the box to fit; with no PRs left it
#                                    hands back to a waiter and closes
#
# One of wait or watch runs per Rex block, its pid in the block's state file;
# either exits when Claude does. The box is a Rex floating layer sized in
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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_tracking  # noqa: E402

TICK = 2
# Cells the floating layer's frame takes, until measured.
FRAME = (3, 3)
# How long a waiter that opened the box waits for the box to take over.
HANDOFF = 15


def _state_path(block):
    return pr_tracking._path("float", re.sub(r"[^\w.-]", "_", block) + ".json")


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def claude_pid():
    """The nearest ancestor process named claude."""
    pid = os.getppid()
    for _ in range(10):
        out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True)
        fields = out.stdout.split(None, 1)
        if len(fields) < 2:
            return None
        if os.path.basename(fields[1].strip()) == "claude":
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
    return not state.get("claude_pid") or _alive(state["claude_pid"])


def running(block):
    """Whether the box is showing PRs for this Rex block."""
    state = _state(block)
    return state.get("mode") == "watch" and _alive(state.get("watcher_pid"))


def rex(method, args):
    out = subprocess.run(
        ["rex", "api", "call", "-s", os.environ.get("REX_SESSION", ""), method, json.dumps(args)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"rex {method} failed")
    return json.loads(out.stdout or "{}")


def block_size(block):
    out = subprocess.run(
        ["rex", "block", "call", "-s", os.environ.get("REX_SESSION", ""), "-b", block, "size", "{}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    data = json.loads(out.stdout) if out.returncode == 0 else {}
    return data.get("columns"), data.get("rows")


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


def lines(state):
    session_id, cwd = state.get("session_id"), state.get("cwd") or os.path.expanduser("~")
    common = pr_tracking.git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    branch = pr_tracking.git(cwd, "branch", "--show-current")
    here = os.path.basename(os.path.dirname(common)) if common else ""
    rows = []
    for pr, current in pr_tracking.prs(session_id, cwd, common, branch):
        repo = pr_tracking.repo_of(pr.get("url"))
        prefix = "" if repo == here else repo
        rows.append((current, *cells(pr, prefix)))
    if not rows:
        return []
    t = pr_tracking
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


def bounds(claude_block, rect, body, frame):
    """[x, y, w, h] for a box holding body at the top right of rect, or None."""
    cols, rows = block_size(claude_block)
    if not cols or not rows:
        return None
    x, y, w, h = rect
    win_cols, win_rows = cols / w, rows / h
    want = (max(len(ANSI.sub("", line)) for line in body) + frame[0], len(body) + frame[1])
    bw, bh = min(want[0] / win_cols, w), min(want[1] / win_rows, h)
    return [round(x + w - bw, 4), round(y, 4), round(bw, 4), round(bh, 4)], (win_cols, win_rows)


def _spawn(mode, claude_block):
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), mode, claude_block],
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
    state.update(session_id=session_id, cwd=cwd, claude_pid=int(pid) if pid else None)
    pr_tracking._write_json(_state_path(block), state)
    if not _alive(state.get("watcher_pid")):
        _spawn("wait", block)


def wait(claude_block):
    _claim(claude_block, "wait")
    while True:
        state = _state(claude_block)
        if not _mine(state):
            return
        body = lines(state)
        if body:
            window, rect, _ = locate(rex("session.view", {}), claude_block)
            if not rect:
                return
            placed = bounds(claude_block, rect, body, FRAME)
            if placed:
                break
        time.sleep(TICK)
    rex(
        "session.new_layer",
        {
            "window_id": window,
            "bounds": placed[0],
            "layout": {
                "block": {
                    "flavor": "com.superlogical.terminal.shell",
                    "label": "PRs",
                    "options": {
                        "command": [sys.executable, os.path.abspath(__file__), "watch", claude_block],
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
        if _state(claude_block).get("watcher_pid") != os.getpid():
            return
        time.sleep(1)


def watch(claude_block):
    me = os.environ.get("REX_BLOCK", "")
    _claim(claude_block, "watch")
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(0))
    sys.stdout.write("\033[?25l")
    frame = list(FRAME)
    drawn, placed, asked = None, None, None
    try:
        while True:
            state = _state(claude_block)
            if not _mine(state):
                return
            _, rect, _ = locate(view := rex("session.view", {}), claude_block)
            _, _, layer = locate(view, me)
            if not rect or not layer:
                return
            body = lines(state)
            if not body:
                _spawn("wait", claude_block)
                return
            if body != drawn:
                sys.stdout.write("\033[H\033[2J" + "\r\n".join(body))
                sys.stdout.flush()
                drawn = body
            # Learn the frame from the last resize once Rex has applied it.
            if asked:
                have = block_size(me)
                if all(have) and have != asked[2:]:
                    frame = [asked[0] - have[0], asked[1] - have[1]]
            fit = bounds(claude_block, rect, body, frame)
            if fit:
                (bx, by, bw, bh), (win_cols, win_rows) = fit
                if [bx, by, bw, bh] != placed:
                    rex("session.resize_layer", {"layer_id": layer["layer_id"], "bounds": [bx, by, bw, bh]})
                    placed = [bx, by, bw, bh]
                    inner = (max(len(ANSI.sub("", line)) for line in body), len(body))
                    asked = (round(bw * win_cols), round(bh * win_rows), *inner)
            time.sleep(TICK)
    finally:
        with contextlib.suppress(Exception):
            _, _, layer = locate(rex("session.view", {}), me)
            if layer:
                rex("session.close_layer", {"layer_id": layer["layer_id"]})


if __name__ == "__main__":
    mode, args = sys.argv[1:2], sys.argv[2:]
    with contextlib.suppress(Exception):
        if mode == ["ensure"]:
            ensure(*args[:3])
        elif mode == ["wait"]:
            wait(args[0])
    if mode == ["watch"]:
        watch(args[0])
