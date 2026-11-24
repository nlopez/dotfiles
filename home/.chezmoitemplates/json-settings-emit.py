import json
import sys


def _align_keys(new, old):
    # JSON objects are unordered: lay out new's keys in old's order (new keys
    # last), recursing into lists by index, so reordering by the app that owns
    # the file never shows up as a diff.
    if isinstance(new, dict) and isinstance(old, dict):
        keys = [k for k in old if k in new] + [k for k in new if k not in old]
        return {k: _align_keys(new[k], old.get(k)) for k in keys}
    if isinstance(new, list) and isinstance(old, list):
        return [_align_keys(n, old[i]) if i < len(old) else n for i, n in enumerate(new)]
    return new


def emit_settings(result, current_raw, **dumps_kwargs):
    # Write the existing bytes back when nothing changed semantically, so
    # formatting and trailing-newline differences never produce a diff.
    try:
        original = json.loads(current_raw) if current_raw.strip() else None
    except Exception:
        original = None
    if original is not None and result == original:
        sys.stdout.write(current_raw)
        return
    out = json.dumps(_align_keys(result, original), indent=2, **dumps_kwargs)
    sys.stdout.write(out + ("" if current_raw and not current_raw.endswith("\n") else "\n"))
