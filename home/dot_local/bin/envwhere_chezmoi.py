import json
import os
import re
import sys

ACTION = re.compile(r"\{\{.*?\}\}", re.S)
# Actions that render nothing themselves: control flow, comments, variables.
SILENT = re.compile(r"^\{\{-?\s*(/\*|if\b|else\b|end\b|range\b|with\b|define\b|block\b|break\b|continue\b|\$\w+\s*:?=)")


def classify(src):
    """Per source line: ('text', s) | ('pattern', regex) | ('emit', None) | ('silent', None)."""
    spans = [(m.start(), m.end()) for m in ACTION.finditer(src)]
    out, pos = [], 0
    for line in src.split("\n"):
        start, end = pos, pos + len(line)
        pos = end + 1
        pieces, cur, covered, emits = [], start, False, False
        for a, b in spans:
            if b <= start or a >= end:
                continue
            if a > cur:
                pieces.append(re.escape(src[cur:a]))
            pieces.append(".*")
            covered = True
            if a >= start and not SILENT.match(src[a:b]):
                emits = True
            cur = max(cur, b)
        if not covered:
            out.append(("text", line.strip()))
            continue
        if cur < end:
            pieces.append(re.escape(src[cur:end]))
        literal = "".join(p for p in pieces if p != ".*")
        if not re.sub(r"\\(.)", r"\1", literal).strip():
            out.append(("emit" if emits else "silent", None))
        else:
            out.append(("pattern", re.compile(r"\s*" + "".join(pieces).strip() + r"\s*")))
    return out


INCLUDE = re.compile(r'^\{\{-?\s*(?:template|includeTemplate)\s+"([^"]+)"')


def align(src_path, src_text, tgt, tmpl_dir, depth=0):
    """Map 0-based index into tgt (list of lines) -> (source path, 1-based line, via)."""
    lines = src_text.split("\n")
    kinds = classify(src_text)
    n, m = len(kinds), len(tgt)

    def score(i, j):
        kind, val = kinds[i]
        t = tgt[j].strip()
        if kind == "text":
            # Blank lines anchor nothing and would let an include's blank
            # lines pair with unrelated blanks after it.
            return 3 if val and val == t else 0
        if kind == "pattern":
            return 2 if val.fullmatch(tgt[j]) else 0
        return 0

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            s = score(i, j)
            row[j] = max(nxt[j], row[j + 1], (s + nxt[j + 1]) if s else 0)
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        s = score(i, j)
        if s and dp[i][j] == s + dp[i + 1][j + 1]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1

    mapping = {j: i for i, j in pairs}
    includes = {}
    bounds = [(-1, -1)] + pairs + [(n, m)]
    for (ia, ja), (ib, jb) in zip(bounds, bounds[1:], strict=False):
        gap = list(range(ja + 1, jb))
        if not gap:
            continue
        # Unmatched target lines come from an action that emits text (an
        # included template, a rendered value); failing that, from source
        # lines whose content no longer matches.
        cands = [k for k in range(ia + 1, ib) if kinds[k][0] != "silent" and kinds[k] != ("text", "")]
        emit = [k for k in cands if kinds[k][0] == "emit"]
        if not emit and len(cands) == len(gap):
            mapping.update(zip(gap, cands, strict=False))
            continue
        target = (emit or cands or [max(ia, 0)])[0]
        for g in gap:
            mapping[g] = target
        # A lone include in the gap rendered these lines: align them against it.
        inc = INCLUDE.match(lines[target].strip()) if len(emit) == 1 and depth < 4 else None
        inc_path = os.path.join(tmpl_dir, inc.group(1)) if inc and tmpl_dir else None
        if inc_path and os.path.isfile(inc_path):
            with open(inc_path) as f:
                sub = align(inc_path, f.read(), [tgt[g] for g in gap], tmpl_dir, depth + 1)
            via = f"{src_path}:{target + 1}"
            for k, (sp, sl, sv) in sub.items():
                includes[gap[k]] = (sp, sl, sv or via)
    out = {j: (src_path, i + 1, None) for j, i in mapping.items()}
    out.update(includes)
    return out


def tilde(path, home):
    return "~" + path[len(home) :] if path.startswith(home + "/") else path


def main():
    managed_path, home = sys.argv[1], sys.argv[2]
    try:
        with open(managed_path) as f:
            managed = json.load(f)
    except (OSError, ValueError):
        managed = {}
    # Symlink entries point elsewhere; the file they resolve to has its own entry.
    by_target = {
        v["absolute"]: (v["sourceAbsolute"], v["sourceRelative"])
        for v in managed.values()
        if isinstance(v, dict)
        and "absolute" in v
        and not os.path.basename(v.get("sourceAbsolute", "")).startswith("symlink_")
    }
    cache = {}
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        path, _, line = raw.rpartition(":")
        if not path or not line.isdigit():
            continue
        real = os.path.realpath(path)
        entry = by_target.get(path) or by_target.get(real)
        if not entry or not os.path.isfile(entry[0]):
            continue
        source, relative = entry
        tmpl_dir = os.path.join(source[: -len(relative)], ".chezmoitemplates")
        shown = tilde(source, home)
        name = os.path.basename(source)
        if name.endswith(".age") or name.startswith("modify_"):
            print(f"{raw}\t{shown} (target line {line})")
            continue
        if not name.endswith(".tmpl"):
            print(f"{raw}\t{shown}:{line}")
            continue
        if real not in cache:
            try:
                with open(source) as s, open(real) as t:
                    cache[real] = align(source, s.read(), t.read().split("\n"), tmpl_dir)
            except (OSError, UnicodeDecodeError):
                cache[real] = {}
        hit = cache[real].get(int(line) - 1)
        if not hit:
            print(f"{raw}\t{shown} (target line {line})")
            continue
        sp, sl, via = hit
        print(f"{raw}\t{tilde(sp, home)}:{sl}" + (f" (via {os.path.basename(via)})" if via else ""))


main()
