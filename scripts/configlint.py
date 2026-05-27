#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Lint rendered chezmoi templates.

Renders the full source tree and runs all checks.

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


# ── Chezmoi helpers ──────────────────────────────────────────────────────────


SOURCE_ROOT: str = ""
TMPDIR: str = ""
# Per-run isolated persistent state + cache, so concurrent lint runs (or a
# lint run racing an interactive `chezmoi apply`) don't collide on the
# boltdb lock at ~/.local/share/chezmoi/chezmoistate.boltdb.
PERSISTENT_STATE: str = ""
CACHE_DIR: str = ""


def chezmoi(*args: str, destination: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run chezmoi with the given args.

    destination overrides TMPDIR for this call only (used by the matrix loop
    so each OS × machine render goes to its own isolated directory).
    """
    return subprocess.run(
        [
            CHEZMOI,
            "--source",
            SOURCE_ROOT,
            "--destination",
            destination if destination is not None else TMPDIR,
            "--persistent-state",
            PERSISTENT_STATE,
            "--cache",
            CACHE_DIR,
            *args,
        ],
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
    # chezmoi strips the executable_ prefix in the rendered tree, so the
    # rendered filename is just "brew" (not "executable_brew").
    "brew",
}
# Paths are relative to TMPDIR (the rendered destination), so they use
# destination naming (.config, .local, .oh-my-zsh) not source naming.
SHELLCHECK_PATHS = [
    "Library/Application Support",
    ".config",
    ".local",
    ".oh-my-zsh",
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
    """Render a single source template to a string via `chezmoi cat`.

    tmpl must be an absolute path inside SOURCE_ROOT (not a rendered path).
    """
    dest = chezmoi("target-path", str(tmpl))
    if dest.returncode != 0 or not dest.stdout.strip():
        return None, f"target-path failed for {tmpl}"
    target = dest.stdout.strip()
    result = chezmoi("cat", target)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout, None


# ── Main ─────────────────────────────────────────────────────────────────────


def _source_to_targets(files: list[str]) -> list[str]:
    """Resolve repo-relative source paths to their TMPDIR destination paths.

    Each path is resolved via `chezmoi target-path`; files that cannot be
    mapped (e.g. .chezmoidata entries) are silently skipped.
    """
    source_root = Path(SOURCE_ROOT)
    targets: list[str] = []
    for raw in files:
        p = Path(raw)
        try:
            rel_to_source = p.relative_to("home")
        except ValueError:
            continue
        abs_source = str(source_root / rel_to_source)
        result = chezmoi("target-path", abs_source)
        if result.returncode == 0 and result.stdout.strip():
            targets.append(result.stdout.strip())
    return targets


# Segment names that force a full run because a change there can affect any
# rendered output (shared data or template fragments).
_FULL_RUN_SEGMENTS = frozenset({".chezmoidata", ".chezmoitemplates"})


def categorize_changes(files: list[str]) -> set[str]:
    """Map changed source files to the lint categories they affect.

    Returns {"all"} when a full run is required (no files given, shared
    data/templates changed, modify_* script changed, or the file's impact
    cannot be determined statically).  Otherwise returns a subset of
    {"shellcheck", "xmllint", "git", "ssh", "signers"}.
    """
    if not files:
        return {"all"}

    categories: set[str] = set()
    for raw in files:
        p = Path(raw)
        s = "/".join(p.parts)
        name = p.name
        stem = name.removesuffix(".tmpl")

        # Shared data / shared templates / modify scripts → must full-run.
        if _FULL_RUN_SEGMENTS & set(p.parts):
            return {"all"}
        if any(part.startswith("modify_") for part in p.parts):
            return {"all"}

        # git config files (config.tmpl, include files, allowed_signers, ignore …)
        if "dot_config/git" in s:
            if "allowed_signers" in name:
                categories.add("signers")
            else:
                categories.add("git")

        # SSH config
        elif "dot_ssh" in p.parts:
            categories.add("ssh")

        # Plist
        elif stem.endswith(".plist"):
            categories.add("xmllint")

        # Shell files: zsh scripts, oh-my-zsh custom files, .sh executables,
        # and the rendered `brew` wrapper (source: executable_brew.tmpl).
        # Strip the chezmoi dot_ prefix from stem before matching so that
        # top-level files like dot_zshrc.tmpl (stem=dot_zshrc) are recognised.
        elif (
            stem.removeprefix("dot_").endswith(("zsh", "zshrc", "zshenv", "zprofile"))
            or "exact_dot_oh-my-zsh" in p.parts
            or (name.startswith("executable_") and stem.endswith(".sh"))
            or stem == "executable_brew"  # noqa: SIM114  (readable as-is)
        ):
            categories.add("shellcheck")

        # Anything we can't classify statically → safest to do a full run.
        else:
            return {"all"}

    return categories


def main() -> int:
    global SOURCE_ROOT, TMPDIR, PERSISTENT_STATE, CACHE_DIR

    parser = argparse.ArgumentParser(
        description="Lint rendered chezmoi templates",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help=(
            "Source files to lint (repo-relative paths under home/). "
            "When provided, only the affected lint categories are run. "
            "Omit for a full run (default when called without arguments)."
        ),
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    SOURCE_ROOT = str(repo_root / "home")
    source_root = Path(SOURCE_ROOT)

    categories = categorize_changes(args.files)
    selective = "all" not in categories

    # ── Render the source tree (or a targeted subset) ──────────────────────

    TMPDIR = tempfile.mkdtemp(prefix="chezmoi-lint-")
    # Isolated state/cache for the whole lint run — see PERSISTENT_STATE note.
    state_dir = tempfile.mkdtemp(prefix="chezmoi-lint-state-")
    PERSISTENT_STATE = os.path.join(state_dir, "chezmoistate.boltdb")
    CACHE_DIR = os.path.join(state_dir, "cache")
    os.makedirs(CACHE_DIR, exist_ok=True)

    if selective:
        targets = _source_to_targets(args.files)
        if not targets:
            print("configlint: could not resolve any changed files to targets", file=sys.stderr)
            return 1
        result = chezmoi("apply", "--force", "--no-tty", "--keep-going", *targets)
    else:
        result = chezmoi("apply", "--force", "--no-tty", "--keep-going")

    # Tolerate partial failures (e.g. 1Password timeout, missing external
    # tool) as long as some files were rendered.
    if result.returncode != 0 and result.stderr.strip():
        print(
            f"configlint: chezmoi apply had errors (continuing with partial render):\n"
            f"  {result.stderr.strip().splitlines()[0]}",
            file=sys.stderr,
        )

    if not TMPDIR or not (p := Path(TMPDIR)).is_dir() or not any(p.iterdir()):
        print("configlint: chezmoi render produced no output", file=sys.stderr)
        return 1

    failed = 0
    shell_count = 0
    plist_count = 0
    git_count = 0
    ssh_count = 0
    signers_count = 0

    # ── Shellcheck (shell scripts — not covered by prettier) ───────────────

    if "all" in categories or "shellcheck" in categories:
        shell_paths: list[Path] = []
        for base in SHELLCHECK_PATHS:
            full = Path(TMPDIR) / base
            if full.exists():
                for pattern in SHELL_FILES:
                    shell_paths.extend(full.rglob(pattern))
        shell_paths = sorted(set(x for x in shell_paths if x.is_file()))
        for path in shell_paths:
            shell_count += 1
            print(f"configlint: shellcheck {rel(path)}")
            if not lint_shellcheck(path):
                print(f"  FAIL: shellcheck {rel(path)}", file=sys.stderr)
                failed += 1

    # ── xmllint (plist files — not covered by prettier) ────────────────────

    if "all" in categories or "xmllint" in categories:
        plist_paths = p.rglob("*.plist")
        for path in plist_paths:
            if not path.is_file():
                continue
            plist_count += 1
            print(f"configlint: xmllint {rel(path)}")
            if not lint_xmllint(path):
                print(f"  FAIL: xmllint {rel(path)}", file=sys.stderr)
                failed += 1

    # ── Git config + SSH config + allowed_signers (current machine) ────────
    #
    # render_and_check_git/ssh call render_template() which expects SOURCE_ROOT
    # paths, not rendered-tree paths — pass source_root here, not p (TMPDIR).

    if "all" in categories or "git" in categories:
        git_source = source_root / "dot_config" / "git"
        if git_source.exists():
            git_count += 1
            print("configlint: git config current")
            failed += render_and_check_git(git_source, p, "current")

    if "all" in categories or "ssh" in categories:
        ssh_source = source_root / "dot_ssh"
        if ssh_source.exists():
            ssh_count += 1
            print("configlint: ssh config current")
            failed += render_and_check_ssh(ssh_source, p, "current")

    if "all" in categories or "signers" in categories:
        signers_count += 1
        print("configlint: allowed_signers")
        failed += check_allowed_signers(source_root)

    # ── Extra renders for other OS × machine-type combos ───────────────────
    # Only run the matrix when git or ssh configs may have changed.

    if "all" in categories or categories & {"git", "ssh"}:
        for os_name, machine in MATRIX:
            tag = f"{os_name}_{1 if machine['work'] else 0}_{1 if machine['personal'] else 0}"
            label = f"{os_name}/{'work' if machine['work'] else 'personal'}"
            # Each matrix entry renders into its own directory so runs don't
            # overwrite each other and the existence checks below are reliable.
            tmp_extra = tempfile.mkdtemp(prefix=f"chezmoi-lint-{tag}-")

            data_env = {
                "CHEZMOI_OS": os_name,
                "CHEZMOI_WORK": "1" if machine["work"] else "0",
                "CHEZMOI_PERSONAL": "1" if machine["personal"] else "0",
            }

            old_env = os.environ.copy()
            try:
                os.environ.update(data_env)
                # Pass destination=tmp_extra so this render goes to its own
                # directory instead of overwriting the main TMPDIR render.
                extra = chezmoi("apply", "--force", "--no-tty", destination=tmp_extra)
                if extra.returncode == 0:
                    extra_path = Path(tmp_extra)
                    if extra_path.is_dir() and any(extra_path.iterdir()):
                        # Check for rendered paths (.config/git, .ssh) — the
                        # destination tree uses dot-prefixed names, not source names.
                        if ("all" in categories or "git" in categories) and (extra_path / ".config" / "git").exists():
                            git_count += 1
                            print(f"configlint: git config {label}")
                            failed += render_and_check_git(
                                source_root / "dot_config" / "git",
                                extra_path,
                                label,
                            )
                        if ("all" in categories or "ssh" in categories) and (extra_path / ".ssh").exists():
                            ssh_count += 1
                            print(f"configlint: ssh config {label}")
                            failed += render_and_check_ssh(
                                source_root / "dot_ssh",
                                extra_path,
                                label,
                            )
            finally:
                os.environ.clear()
                os.environ.update(old_env)

    total = shell_count + plist_count + git_count + ssh_count + signers_count
    mode = f", selective: {len(args.files)} file(s)" if selective else ""
    print(
        f"templates: checked {total} files "
        f"(shellcheck={shell_count}, xmllint={plist_count}, "
        f"git={git_count}, ssh={ssh_count}, allowed_signers={signers_count}{mode})",
        file=sys.stderr,
    )

    if failed:
        print(f"templates: {failed} failed", file=sys.stderr)
        return 1

    print("templates: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
