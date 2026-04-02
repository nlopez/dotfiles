#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

OSES = ["darwin", "linux", "windows"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render chezmoi templates and lint .json files"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print filename and variable inputs for each check",
    )
    args = parser.parse_args()

    chezmoi_root = Path(
        subprocess.check_output(["chezmoi", "source-path"]).decode().strip()
    )

    errors = 0

    # Lint plain .json files (no templating needed)
    for json_file in sorted(chezmoi_root.rglob("*.json")):
        errors += lint_json(
            json_file.read_text(),
            str(json_file.relative_to(chezmoi_root)),
            args.verbose,
        )

    # Render and lint .json.tmpl files for each OS
    for os_name in OSES:
        override_data, user_data = build_data(chezmoi_root, os_name)

        for tmpl in sorted(chezmoi_root.rglob("*.json.tmpl")):
            label = f"{os_name}/{tmpl.relative_to(chezmoi_root)}"
            errors += render_and_lint(
                tmpl, override_data, user_data, label, args.verbose
            )

    if errors:
        print(f"\n{errors} error(s)", file=sys.stderr)
        sys.exit(1)
    print("\nAll checks passed.")


def build_data(chezmoi_root: Path, os_name: str) -> tuple[dict, dict]:
    override_data: dict = {
        "chezmoi": {
            "os": os_name,
            "osRelease": {
                "id": "ubuntu",
                "ubuntuCodename": "noble",
            },
        },
    }

    user_data: dict = {
        "personal": True,
        "work": False,
        "wsl": False,
        "headless": False,
        "ephemeral": False,
    }

    pkg_file = chezmoi_root / ".chezmoidata" / os_name / "packages.yaml"
    if pkg_file.exists():
        with open(pkg_file) as f:
            user_data.update(yaml.safe_load(f))

    return override_data, user_data


def print_verbose(label: str, override_data: dict, user_data: dict) -> None:
    chezmoi = override_data["chezmoi"]
    vars_: dict = {"chezmoi.os": chezmoi["os"]}
    vars_.update({k: v for k, v in user_data.items() if k != "packages"})
    vars_str = "  ".join(f"{k}={json.dumps(v)}" for k, v in vars_.items())
    print(f"  {label}  [{vars_str}]")


def render_and_lint(
    tmpl: Path, override_data: dict, user_data: dict, label: str, verbose: bool
) -> int:
    if verbose:
        print_verbose(label, override_data, user_data)
    else:
        print(f"jsonlint: {label}")

    merged = {**user_data, **override_data}
    try:
        result = subprocess.run(
            [
                "chezmoi",
                "execute-template",
                "--file",
                "--override-data",
                json.dumps(merged),
                str(tmpl),
            ],
            capture_output=True,
            text=True,
        )
    except Exception as e:
        print(f"RENDER ERROR: {label}: {e}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(f"RENDER FAILED: {label}\n{result.stderr}", file=sys.stderr)
        return 1

    return lint_json(result.stdout, label, verbose)


def lint_json(content: str, label: str, verbose: bool = False) -> int:
    if verbose:
        print(f"jsonlint: {label}")
    else:
        print(f"jsonlint: {label}")

    # Strip JS-style line comments before parsing, since Zed config files use them
    lines = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        # Inline comment: remove everything after an unquoted //
        out = _strip_inline_comment(line)
        lines.append(out)

    # Remove trailing commas before closing braces/brackets (common in Zed configs)
    cleaned = _remove_trailing_commas("\n".join(lines))

    try:
        json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  JSON ERROR: {e}", file=sys.stderr)
        return 1

    return 0


def _strip_inline_comment(line: str) -> str:
    """Remove a // line comment that appears outside of a quoted string."""
    in_string = False
    escape_next = False
    i = 0
    while i < len(line):
        ch = line[i]
        if escape_next:
            escape_next = False
        elif ch == "\\" and in_string:
            escape_next = True
        elif ch == '"':
            in_string = not in_string
        elif not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            return line[:i].rstrip()
        i += 1
    return line


def _remove_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (JSONC quirk used in Zed configs)."""
    import re

    return re.sub(r",(\s*[}\]])", r"\1", text)


if __name__ == "__main__":
    main()
