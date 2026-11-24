#!/usr/bin/env python3
"""Print the package changes the next `chezmoi apply` would make.

Templates call this at render time and embed its output in the install
scripts, so `chezmoi diff` lists pending installs and removals. Empty output
means the host already matches the declared set, and the script renders empty.

  package-plan.py nix  <declared-json> <profile>
  package-plan.py mise <declared-json> <mise> <global-config>
  package-plan.py brew <brew> <cleanup: true|false>   (Brewfile on stdin)

Every subcommand is read-only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

NIX_MANIFEST = ".dotfiles-manifest.json"


def run(args: list[str], stdin: str | None = None, stderr: bool = False) -> str:
    env = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", MISE_QUIET="1")
    proc = subprocess.run(args, input=stdin, capture_output=True, text=True, env=env, check=False)
    return proc.stdout + (proc.stderr if stderr else "")


def nix(declared: str, profile: str) -> list[str]:
    want = json.loads(declared)
    try:
        with open(os.path.join(profile, NIX_MANIFEST)) as f:
            have = json.load(f)
    except FileNotFoundError:
        if os.path.exists(profile):
            return ["rebuild: profile has no package manifest"]
        return [f"+ {p}" for p in want["packages"]]

    lines = [f"+ {p}" for p in want["packages"] if p not in have.get("packages", [])]
    lines += [f"- {p}" for p in have.get("packages", []) if p not in want["packages"]]
    if have.get("rev") != want["rev"]:
        lines.append(f"nixpkgs {str(have.get('rev'))[:12]} -> {want['rev'][:12]} (rebuilds every package)")
    if have.get("unfree") != want["unfree"]:
        lines.append("unfree allowlist changed")
    if have.get("template") != want["template"] and len(lines) == 0:
        lines.append("flake template changed")
    return lines


def mise_matches(installed: str, requested: str) -> bool:
    return requested == "latest" or installed == requested or installed.startswith(requested + ".")


def mise(declared: str, mise_bin: str, global_config: str) -> list[str]:
    if not os.access(mise_bin, os.X_OK):
        return []
    want: dict[str, str] = json.loads(declared)
    installed: dict[str, list[dict]] = json.loads(run([mise_bin, "ls", "--installed", "--json"]) or "{}")
    prunable: dict[str, list[dict]] = json.loads(run([mise_bin, "ls", "--prunable", "--json"]) or "{}")

    lines = []
    for tool, version in sorted(want.items()):
        versions = [v["version"] for v in installed.get(tool, [])]
        if not any(mise_matches(v, version) for v in versions):
            lines.append(f"+ {tool}@{version}")

    # `mise prune` runs against the config this apply writes. A version kept
    # only by the current global config goes once that config stops asking for it.
    remove = {(tool, v["version"]) for tool, vs in prunable.items() for v in vs}
    for tool, vs in installed.items():
        for v in vs:
            source = (v.get("source") or {}).get("path")
            if source == global_config and not (tool in want and mise_matches(v["version"], want[tool])):
                remove.add((tool, v["version"]))
    lines += [f"- {tool}@{version}" for tool, version in sorted(remove)]
    return lines


def brew(brew_bin: str, cleanup: str) -> list[str]:
    if not os.access(brew_bin, os.X_OK):
        return []
    brewfile = sys.stdin.read()
    lines = []
    check = run([brew_bin, "bundle", "check", "--verbose", "--no-upgrade", "--file=-"], brewfile, stderr=True)
    for m in re.finditer(r"^→ (\S+) (\S+) needs to be installed", check, re.M):
        lines.append(f"+ {m.group(1).lower()} {m.group(2)}")
    # Undeclared installs are drift either way; only brew.cleanup decides
    # whether apply removes them.
    kinds = {"untap": "tap", "casks": "cask", "formulae": "formula", "Mac App Store apps": "mas"}
    out = run([brew_bin, "bundle", "cleanup", "--file=-"], brewfile)
    mark = "-" if cleanup == "true" else "?"
    section = None
    extras: dict[str, list[str]] = {}
    for line in out.splitlines():
        if line.startswith("Would `brew cleanup`"):
            break
        m = re.match(r"^Would (\w+)(?: (.+))?:$", line)
        if m:
            section = kinds.get(m.group(2) or m.group(1), m.group(2) or m.group(1))
        elif section and line.strip():
            extras.setdefault(section, []).append(line.strip())

    deps = brew_group_deps(brew_bin, extras.get("formula", []))
    for kind, names in extras.items():
        for name in names:
            if kind == "formula" and name not in deps:
                continue
            under = f"  (+ {', '.join(deps[name])})" if kind == "formula" and deps[name] else ""
            lines.append(f"{mark} {kind} {name}{under}")
    if extras and cleanup != "true":
        lines.append("? = installed but undeclared; kept because brew.cleanup is false")
    return lines


def brew_group_deps(brew_bin: str, formulae: list[str]) -> dict[str, list[str]]:
    """Map each undeclared top-level formula to the undeclared formulae it pulls in.

    A formula that another undeclared formula depends on appears only under its
    top-level parents. Deps come from the formula definitions: `brew deps
    --installed` reads install receipts, which miss some (hf -> certifi).
    """
    if not formulae:
        return {}
    out = run([brew_bin, "deps", "--for-each", "--full-name", *formulae])
    deps = {}
    for line in out.splitlines():
        name, _, rest = line.partition(":")
        deps[name.strip()] = set(rest.split())
    pending = set(formulae)
    nested = set().union(*(deps.get(name, set()) for name in formulae)) & pending
    return {name: sorted(deps.get(name, set()) & pending) for name in formulae if name not in nested}


def main() -> None:
    cmd, *args = sys.argv[1:]
    lines = {"nix": nix, "mise": mise, "brew": brew}[cmd](*args)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
