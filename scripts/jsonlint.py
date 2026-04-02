#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
from pathlib import Path

import json5
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

    try:
        json5.loads(content)
    except ValueError as e:
        print(f"  JSON ERROR in {label}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    main()
