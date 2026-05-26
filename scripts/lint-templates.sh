#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Lint rendered chezmoi templates.

Uses `chezmoi apply --destination` to render the entire source tree into a
temporary directory, then runs each linter recursively over that tree.

NOTE: Only checks file types that prettier doesn't cover:
  - Shell scripts (.zshrc, .zshenv, .zprofile, .zsh, etc.) → shellcheck
  - Plist files (.plist)                            → xmllint

These were previously checked by yamllint, taplo, and jsonlint, but prettier
now handles YAML, TOML, and JSON via `prettier --write`.

Skipped (no linter available or not needed):
  Brewfile, terraformrc, git/config, SSH config,
  rclone.conf, SSH keys (.pub), modify_ templates,
  chezmoi special dirs (.chezmoi*/).
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


CHEZMOI = "chezmoi"


def chezmoi(*args: str) -> subprocess.CompletedProcess[str]:
    """Run chezmoi with the given args."""
    return subprocess.run(
        [CHEZMOI, "--source", SOURCE_ROOT, "--destination", TMPDIR, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def rel(path: Path) -> str:
    """Return path relative to TMPDIR."""
    return str(path.relative_to(TMPDIR))


# Shellcheck


def lint_shellcheck(path: Path) -> bool:
    result = subprocess.run(
        ["shellcheck", "--exclude=SC1091,SC2154", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(f"  {result.stderr.strip()}\n")
    return result.returncode == 0


# xmllint (plist validation)


def lint_xmllint(path: Path) -> bool:
    result = subprocess.run(
        ["xmllint", "--noout", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(f"  {result.stderr.strip()}\n")
    return result.returncode == 0


SHELL_FILES = {"*.zshrc", "*.zshenv", "*.zprofile", "00_custom.zsh", "_chezmoi", "executable_brew"}
PLIST_FILES = {"*.plist"}


SHELLCHECK_PATHS = [
    "Library/Application Support",
    "dot_config",
    "dot_local",
    "exact_dot_oh-my-zsh",
]


def find_matching(root: Path, patterns: set[str]) -> list[Path]:
    """Find files matching glob patterns under root."""
    results: list[Path] = []
    for pattern in patterns:
        results.extend(root.rglob(pattern))
    return sorted(set(results))


def main() -> int:
    global SOURCE_ROOT, TMPDIR

    parser = argparse.ArgumentParser(description="Lint rendered chezmoi templates")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose output")
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    SOURCE_ROOT = str(repo_root / "home")
    TMPDIR = tempfile.mkdtemp(prefix="chezmoi-lint-")

    if args.verbose:
        print(f"Rendering to {TMPDIR}", file=sys.stderr)

    # Render the entire source tree into TMPDIR
    result = chezmoi("apply", "--force", "--no-tty")
    if result.returncode != 0 and "not found" not in result.stderr:
        sys.stderr.write(f"  chezmoi apply failed:\n{result.stderr.strip()}\n")
        return 1

    if not TMPDIR or not (p := Path(TMPDIR)).is_dir() or not any(p.iterdir()):
        print("templates: chezmoi render produced no output", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"  rendered {len(list(p.rglob('*')))} files", file=sys.stderr)

    failed = 0

    # Shellcheck (shell scripts — not covered by prettier)
    shell_paths: list[Path] = []
    for base in SHELLCHECK_PATHS:
        full = Path(TMPDIR) / base
        if full.exists():
            for pattern in SHELL_FILES:
                shell_paths.extend(full.rglob(pattern))
    shell_paths = sorted(set(x for x in shell_paths if x.is_file()))
    for path in shell_paths:
        if not lint_shellcheck(path):
            print(f"  FAIL: shellcheck {rel(path)}", file=sys.stderr)
            failed += 1

    # xmllint (plist files — not covered by prettier)
    plist_paths = find_matching(p, PLIST_FILES)
    for path in plist_paths:
        if not lint_xmllint(path):
            print(f"  FAIL: xmllint {rel(path)}", file=sys.stderr)
            failed += 1

    if failed:
        print(f"templates: {failed} failed", file=sys.stderr)
        return 1

    print("templates: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
