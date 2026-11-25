#!/usr/bin/env python3
"""Plan and apply declared macOS defaults and default-app handlers.

Templates call `plan` at render time and embed its output in the configure
scripts, so `chezmoi diff` lists settings that drifted from
.chezmoidata/darwin/{defaults,handlers}.yaml. Empty output means the host
matches, and the script renders empty.

  macos-plan.py defaults plan  <declared-json>
  macos-plan.py defaults apply                  (declared JSON on stdin)
  macos-plan.py handlers plan  <declared-json>  (needs duti on PATH)
  macos-plan.py handlers apply                  (declared JSON on stdin)

`apply` changes only the entries that differ.
"""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from typing import Any

# Processes that must restart to pick up a domain's changes.
RESTART = {
    "NSGlobalDomain": ["Finder", "SystemUIServer"],
    "com.apple.finder": ["Finder"],
    "com.apple.desktopservices": ["Finder"],
    "com.apple.dock": ["Dock"],
    "com.apple.spaces": ["Dock"],
    "com.apple.WindowManager": ["Dock"],
    "com.apple.menuextra.clock": ["SystemUIServer"],
}


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def typed(value: Any) -> Any:
    """Turn declared JSON into the Python values plistlib reads back."""
    if isinstance(value, dict):
        if set(value) == {"float"}:
            return float(value["float"])
        return {k: typed(v) for k, v in value.items()}
    if isinstance(value, list):
        return [typed(v) for v in value]
    return value


def same(a: Any, b: Any) -> bool:
    # Strict on type: True == 1 in Python, but -bool and -int are different plist types.
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=False))
    return a == b


def show(value: Any) -> str:
    if value is None:
        return "unset"
    if isinstance(value, bool):
        return str(value).lower()
    return json.dumps(value, separators=(",", ":")) if isinstance(value, dict | list) else str(value)


def defaults_drift(declared: dict[str, dict[str, Any]]) -> list[tuple[str, str, Any, Any]]:
    drift = []
    for domain, keys in declared.items():
        proc = subprocess.run(["defaults", "export", domain, "-"], capture_output=True, check=False)
        live = plistlib.loads(proc.stdout) if proc.returncode == 0 else {}
        for key, want in keys.items():
            want = typed(want)
            have = live.get(key)
            if not same(have, want):
                drift.append((domain, key, have, want))
    return drift


def plist_fragment(value: Any) -> str:
    """The XML for one value, which `defaults write` accepts in place of a -type flag."""
    xml = plistlib.dumps(value, fmt=plistlib.FMT_XML).decode()
    return xml.split('<plist version="1.0">', 1)[1].rsplit("</plist>", 1)[0].strip()


def defaults_cmd(mode: str, declared: dict[str, dict[str, Any]]) -> int:
    drift = defaults_drift(declared)
    if mode == "plan":
        for domain, key, have, want in drift:
            print(f"~ {domain} {key}: {show(have)} → {show(want)}")
        return 0
    restart: set[str] = set()
    for domain, key, _, want in drift:
        proc = run(["defaults", "write", domain, key, plist_fragment(want)])
        if proc.returncode != 0:
            print(f"defaults write {domain} {key} failed: {proc.stderr.strip()}", file=sys.stderr)
            return 1
        restart.update(RESTART.get(domain, []))
    for proc_name in sorted(restart):
        run(["killall", proc_name])
    return 0


def current_handler(target: str) -> str | None:
    proc = run(["duti", "-d", target])
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else None


def handlers_drift(declared: dict[str, dict[str, str]]) -> list[tuple[str, str, str | None, str]]:
    drift = []
    for kind in ("types", "schemes"):
        for target, want in (declared.get(kind) or {}).items():
            have = current_handler(target)
            # LaunchServices stores bundle IDs lowercased.
            if (have or "").lower() != want.lower():
                drift.append((kind, target, have, want))
    return drift


def handlers_cmd(mode: str, declared: dict[str, dict[str, str]]) -> int:
    drift = handlers_drift(declared)
    if mode == "plan":
        for kind, target, have, want in drift:
            label = f"{target}:" if kind == "schemes" else target
            print(f"~ {label} {have or 'unset'} → {want}")
        return 0
    status = 0
    for kind, target, _, want in drift:
        # duti treats a target as a URL scheme when no role is given.
        args = ["duti", "-s", want, target] + (["all"] if kind == "types" else [])
        proc = run(args)
        if proc.returncode != 0:
            print(f"{' '.join(args)} failed: {proc.stderr.strip()}", file=sys.stderr)
            status = 1
    return status


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ("defaults", "handlers") or sys.argv[2] not in ("plan", "apply"):
        print(__doc__, file=sys.stderr)
        return 2
    declared = json.loads(sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read())
    cmd = defaults_cmd if sys.argv[1] == "defaults" else handlers_cmd
    return cmd(sys.argv[2], declared)


if __name__ == "__main__":
    sys.exit(main())
