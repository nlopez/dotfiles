#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Render and validate git and SSH config templates across all machine types.

Checks:
  - git configs (config.tmpl + all include *.tmpl files): render then
    `git config -f <file> --list` for each OS × machine-type combination.
  - SSH config (dot_ssh/config.tmpl): render then
    `ssh -F <file> -G <host>` for each alias pattern.
  - allowed_signers: syntax check (# comments, ≥3 fields per key line).
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from chezmoi_lib import build_data, chezmoi_root, print_verbose, render_template

# OS × machine-type matrix to validate.
MATRIX = [
    ("darwin", {"work": True,  "personal": False}),
    ("darwin", {"work": False, "personal": True}),
    ("linux",  {"work": True,  "personal": False}),
    ("linux",  {"work": False, "personal": True}),
]

# git include files alongside the main config.
GIT_INCLUDES = [
    "config_nlopez",
    "config_nick-lopez_ddog",
    "config_silentshout42",
]

# SSH host aliases to probe with `ssh -G`.
SSH_HOSTS = [
    "github.com",
    "github.com-nlopez",
    "github.com-nick-lopez_ddog",
    "github.com-silentshout42",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    root = chezmoi_root()
    errors = 0

    for os_name, machine in MATRIX:
        data = build_data(root, os_name)
        data.update(machine)
        machine_label = "work" if machine["work"] else "personal"
        label = f"{os_name}/{machine_label}"

        errors += check_git(root, data, label, args.verbose)
        errors += check_ssh(root, data, label, args.verbose)

    errors += check_allowed_signers(root, args.verbose)

    if errors:
        print(f"\n{errors} error(s)", file=sys.stderr)
        sys.exit(1)
    print("\nAll checks passed.")


# ── git config ────────────────────────────────────────────────────────────────

def check_git(root: Path, data: dict, label: str, verbose: bool) -> int:
    errors = 0
    git_dir = root / "dot_config" / "git"

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        # Render the main config and all include files into the same directory
        # so that relative `path = config_nlopez` references in includeIf rules
        # resolve correctly when git follows them.
        files_to_render: list[tuple[str, Path]] = [
            ("config", git_dir / "config.tmpl"),
            *[(name, git_dir / f"{name}.tmpl") for name in GIT_INCLUDES],
        ]

        rendered_main: Path | None = None

        for dest_name, tmpl in files_to_render:
            file_label = f"git/{label}/{dest_name}"
            if verbose:
                print_verbose(file_label, data["chezmoi"]["os"], data)
            else:
                print(f"configlint: {file_label}")

            output, err = render_template(tmpl, data)
            if err is not None or output is None:
                print(f"  RENDER FAILED: {file_label}\n  {err}", file=sys.stderr)
                errors += 1
                continue

            dest = tmpdir / dest_name
            dest.write_text(output)

            # Validate each include independently.
            if dest_name != "config":
                errors += _git_validate(dest, file_label)
            else:
                rendered_main = dest

        # Validate the main config with all includes in place so that any
        # static `include` (not `includeIf`) paths also resolve.
        if rendered_main is not None:
            errors += _git_validate(rendered_main, f"git/{label}/config (full)")

    return errors


def _git_validate(config_file: Path, label: str) -> int:
    result = subprocess.run(
        ["git", "config", "-f", str(config_file), "--list"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr.strip():
        print(f"  GIT CONFIG ERROR in {label}:", file=sys.stderr)
        for line in result.stderr.strip().splitlines():
            print(f"    {line}", file=sys.stderr)
        return 1
    return 0


# ── SSH config ────────────────────────────────────────────────────────────────

def check_ssh(root: Path, data: dict, label: str, verbose: bool) -> int:
    tmpl = root / "dot_ssh" / "config.tmpl"
    file_label = f"ssh/{label}/config"

    if verbose:
        print_verbose(file_label, data["chezmoi"]["os"], data)
    else:
        print(f"configlint: {file_label}")

    output, err = render_template(tmpl, data)
    if err is not None or output is None:
        print(f"  RENDER FAILED: {file_label}\n  {err}", file=sys.stderr)
        return 1

    errors = 0
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ssh_config", delete=False) as f:
        f.write(output)
        tmp_path = f.name

    try:
        for host in SSH_HOSTS:
            result = subprocess.run(
                ["ssh", "-F", tmp_path, "-G", host],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  SSH CONFIG ERROR in {file_label} (host={host}):", file=sys.stderr)
                for line in result.stderr.strip().splitlines():
                    print(f"    {line}", file=sys.stderr)
                errors += 1
    finally:
        os.unlink(tmp_path)

    return errors


# ── allowed_signers ───────────────────────────────────────────────────────────

def check_allowed_signers(root: Path, verbose: bool) -> int:
    """
    Validate allowed_signers syntax.  Each non-blank, non-comment line must be:
      principals  namespaces="git"  keytype  base64-key  [comment...]
    That is, at least 4 whitespace-separated fields.
    """
    path = root / "dot_config" / "git" / "allowed_signers"
    label = "git/allowed_signers"

    if verbose:
        print(f"configlint: {label} [syntax check]")
    else:
        print(f"configlint: {label}")

    if not path.exists():
        print(f"  NOT FOUND: {label}", file=sys.stderr)
        return 1

    errors = 0
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 4:
            print(
                f"  ALLOWED_SIGNERS ERROR at line {lineno}: "
                f"expected ≥4 fields, got {len(fields)}: {raw!r}",
                file=sys.stderr,
            )
            errors += 1

    return errors


if __name__ == "__main__":
    main()
