#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Smart linting for rendered chezmoi templates.

Quick-path: if no `.tmpl` file under home/ has changed, skip entirely.
When templates change, render the full tree once and run all checks.

Checks performed on the current-machine render:
  - Shell scripts (.zshrc, .zshenv, .zprofile, etc.)             → shellcheck
  - Plist files (.plist)                                         → xmllint
  - Git configs (git config --list)                              → git config
  - SSH config (ssh -F -G host)                                  → ssh -G
  - allowed_signers (ssh-keygen -lf)                             → ssh-keygen

Additional renders for other OS × machine-type combos:
  - Git configs (git config --list)
  - SSH config (ssh -F -G host)

NOTE: YAML, JSON, and TOML formatting is handled by the prettier pre-commit
hook — no rendering is needed for those here.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CHEZMOI = "chezmoi"

# OS × machine-type matrix for semantic checks on configs that vary.
MATRIX: list[tuple[str, dict[str, bool]]] = [
    ("darwin", {"work": True, "personal": False}),
    ("darwin", {"work": False, "personal": True}),
    # linux/personal — personal Linux machine (no work plugins)
    # NOTE: work/linux intentionally omitted — no work machines run Linux.
    ("linux", {"work": False, "personal": True}),
]

GIT_INCLUDES = ["config_nlopez", "config_nick-lopez_ddog", "config_silentshout42"]
SSH_HOSTS = [
    "github.com",
    "github.com-nlopez",
    "github.com-nick-lopez_ddog",
    "github.com-silentshout42",
]


# ── Changed-file detection ──────────────────────────────────────────────────


def get_changed_files() -> list[Path]:
    """Return list of changed files in the working tree (since HEAD)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [Path(f) for f in result.stdout.strip().splitlines() if f]
    except FileNotFoundError:
        return []


def has_changed_templates(home: Path) -> bool:
    """True if any .tmpl file under home/ has changed."""
    home_str = str(home)
    for f in get_changed_files():
        try:
            if str(f).startswith(home_str) and f.suffix == ".tmpl":
                return True
        except ValueError:
            pass
    return False


# ── Chezmoi helpers ──────────────────────────────────────────────────────────


SOURCE_ROOT: str = ""
TMPDIR: str = ""


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


# ── Linters ─────────────────────────────────────────────────────────────────

SHELL_FILES: set[str] = {
    "*.zshrc",
    "*.zshenv",
    "*.zprofile",
    "00_custom.zsh",
    "_chezmoi",
    "executable_brew",
}
SHELLCHECK_PATHS = [
    "Library/Application Support",
    "dot_config",
    "dot_local",
    "exact_dot_oh-my-zsh",
]


def lint_shellcheck(path: Path) -> bool:
    result = subprocess.run(
        ["shellcheck", "--exclude=SC1091,SC2154", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(f"  {result.stderr.strip()}\n")
    return result.returncode == 0


PLIST_FILES: set[str] = {"*.plist"}


def lint_xmllint(path: Path) -> bool:
    result = subprocess.run(
        ["xmllint", "--noout", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(f"  {result.stderr.strip()}\n")
    return result.returncode == 0


# ── Git config validation ───────────────────────────────────────────────────


def _git_validate(config_file: Path, label: str) -> int:
    result = subprocess.run(
        ["git", "config", "-f", str(config_file), "--list"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr.strip():
        sys.stderr.write(f"  GIT CONFIG ERROR in {label}:\n")
        for line in result.stderr.strip().splitlines():
            sys.stderr.write(f"    {line}\n")
        return 1
    return 0


def render_and_check_git(config_dir: Path, tmp_dir: Path, label: str) -> int:
    """Render git config template + includes, then validate with `git config --list`."""
    errors = 0
    files_to_render: list[tuple[str, Path]] = [
        ("config", config_dir / "config.tmpl"),
        *[(name, config_dir / f"{name}.tmpl") for name in GIT_INCLUDES],
    ]

    rendered_main: Path | None = None
    for dest_name, tmpl in files_to_render:
        file_label = f"git/{label}/{dest_name}"
        if not tmpl.exists():
            continue

        output, err = render_template(tmpl)
        if err is not None or output is None:
            sys.stderr.write(f"  RENDER FAILED: {file_label}\n  {err}\n")
            return 1

        dest = tmp_dir / dest_name
        dest.write_text(output)

        if dest_name != "config":
            errors += _git_validate(dest, file_label)
        else:
            rendered_main = dest

    if rendered_main is not None:
        errors += _git_validate(rendered_main, f"git/{label}/config (full)")

    return errors


# ── SSH config validation ───────────────────────────────────────────────────


def render_and_check_ssh(ssh_dir: Path, tmp_dir: Path, label: str) -> int:
    """Render SSH config template, then validate with `ssh -F -G`."""
    tmpl = ssh_dir / "config.tmpl"
    file_label = f"ssh/{label}/config"

    if not tmpl.exists():
        return 0

    output, err = render_template(tmpl)
    if err is not None or output is None:
        sys.stderr.write(f"  RENDER FAILED: {file_label}\n  {err}\n")
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
                sys.stderr.write(f"  SSH CONFIG ERROR in {file_label} (host={host}):\n")
                for line in result.stderr.strip().splitlines():
                    sys.stderr.write(f"    {line}\n")
                errors += 1
    finally:
        os.unlink(tmp_path)

    return errors


# ── Allowed signers ─────────────────────────────────────────────────────────


def check_allowed_signers(root: Path) -> int:
    path = root / "dot_config" / "git" / "allowed_signers"

    if not path.exists():
        sys.stderr.write("  NOT FOUND: git/allowed_signers\n")
        return 1

    errors = 0
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        fields = line.split()
        keyline_fields = []
        for f in fields[1:]:  # skip principals
            if "=" not in f:
                keyline_fields = fields[fields.index(f) :]
                break

        if len(keyline_fields) < 2:
            sys.stderr.write(f"  ALLOWED_SIGNERS ERROR at line {lineno}: {raw!r}\n")
            errors += 1
            continue

        key_text = " ".join(keyline_fields) + "\n"
        result = subprocess.run(
            ["ssh-keygen", "-lf", "/dev/stdin"],
            input=key_text,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(f"  ALLOWED_SIGNERS ERROR at line {lineno}: ssh-keygen rejected {raw!r}\n")
            for msg in result.stderr.strip().splitlines():
                sys.stderr.write(f"    {msg}\n")
            errors += 1

    return errors


# ── Helpers ──────────────────────────────────────────────────────────────────


def render_template(tmpl: Path) -> tuple[str | None, str | None]:
    """Render a single template via chezmoi."""
    dest = chezmoi("target-path", str(tmpl))
    if dest.returncode != 0 or not dest.stdout.strip():
        return None, f"target-path failed for {tmpl}"
    target = dest.stdout.strip()
    result = chezmoi("cat", target)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout, None


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    global SOURCE_ROOT, TMPDIR

    parser = argparse.ArgumentParser(
        description="Smart linting for rendered chezmoi templates",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    SOURCE_ROOT = str(repo_root / "home")
    home = Path(SOURCE_ROOT)

    # Quick-path: skip if no .tmpl files changed
    if not has_changed_templates(home):
        if args.verbose:
            print("templates: no .tmpl files changed, skipping", file=sys.stderr)
        return 0

    if args.verbose:
        print("templates: templates changed, rendering and checking", file=sys.stderr)

    # ── Render the full source tree (template dependencies require it) ──────

    TMPDIR = tempfile.mkdtemp(prefix="chezmoi-lint-")

    result = chezmoi("apply", "--force", "--no-tty")
    if result.returncode != 0 and "not found" not in result.stderr:
        sys.stderr.write(f"  chezmoi apply failed:\n{result.stderr.strip()}\n")
        return 1

    if not TMPDIR or not (p := Path(TMPDIR)).is_dir() or not any(p.iterdir()):
        print("templates: chezmoi render produced no output", file=sys.stderr)
        return 1

    failed = 0
    shell_count = 0
    plist_count = 0
    git_count = 0
    ssh_count = 0
    signers_count = 0

    # ── Shellcheck (shell scripts — not covered by prettier) ───────────────

    shell_paths: list[Path] = []
    for base in SHELLCHECK_PATHS:
        full = Path(TMPDIR) / base
        if full.exists():
            for pattern in SHELL_FILES:
                shell_paths.extend(full.rglob(pattern))
    shell_paths = sorted(set(x for x in shell_paths if x.is_file()))
    for path in shell_paths:
        shell_count += 1
        if not lint_shellcheck(path):
            print(f"  FAIL: shellcheck {rel(path)}", file=sys.stderr)
            failed += 1

    # ── xmllint (plist files — not covered by prettier) ────────────────────

    plist_paths = p.rglob("*.plist")
    for path in plist_paths:
        if not path.is_file():
            continue
        plist_count += 1
        if not lint_xmllint(path):
            print(f"  FAIL: xmllint {rel(path)}", file=sys.stderr)
            failed += 1

    # ── Git config + SSH config + allowed_signers (current machine) ────────

    if p.joinpath("dot_config", "git").exists():
        git_count += 1
        failed += render_and_check_git(p / "dot_config" / "git", p, "current")
    if p.joinpath("dot_ssh").exists():
        ssh_count += 1
        failed += render_and_check_ssh(p / "dot_ssh", p, "current")
    signers_count += 1
    failed += check_allowed_signers(Path(SOURCE_ROOT))

    # ── Extra renders for other OS × machine-type combos ───────────────────

    for os_name, machine in MATRIX:
        tag = f"{os_name}_{1 if machine['work'] else 0}_{1 if machine['personal'] else 0}"
        label = f"{os_name}/{'work' if machine['work'] else 'personal'}"
        tmp_extra = tempfile.mkdtemp(prefix=f"chezmoi-lint-{tag}-")

        data_env = {
            "CHEZMOI_OS": os_name,
            "CHEZMOI_WORK": "1" if machine["work"] else "0",
            "CHEZMOI_PERSONAL": "1" if machine["personal"] else "0",
        }

        old_env = os.environ.copy()
        try:
            os.environ.update(data_env)
            extra = chezmoi("apply", "--force", "--no-tty")
            if extra.returncode == 0:
                extra_path = Path(tmp_extra)
                if extra_path.is_dir() and any(extra_path.iterdir()):
                    if extra_path.joinpath("dot_config", "git").exists():
                        git_count += 1
                        failed += render_and_check_git(
                            extra_path / "dot_config" / "git",
                            extra_path,
                            label,
                        )
                    if extra_path.joinpath("dot_ssh").exists():
                        ssh_count += 1
                        failed += render_and_check_ssh(extra_path / "dot_ssh", extra_path, label)
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    total = shell_count + plist_count + git_count + ssh_count + signers_count
    print(
        f"templates: checked {total} files "
        f"(shellcheck={shell_count}, xmllint={plist_count}, "
        f"git={git_count}, ssh={ssh_count}, allowed_signers={signers_count})"
    )

    if failed:
        print(f"templates: {failed} failed", file=sys.stderr)
        return 1

    print("templates: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
