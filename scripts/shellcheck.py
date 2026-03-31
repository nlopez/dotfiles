#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

OSES = ["darwin", "linux", "windows"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render chezmoi templates and shellcheck .sh files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print filename and variable inputs for each check")
    args = parser.parse_args()

    chezmoi_root = Path(
        subprocess.check_output(["chezmoi", "source-path"]).decode().strip()
    )

    errors = 0

    for os_name in OSES:
        scripts_dir = chezmoi_root / ".chezmoiscripts" / os_name
        if not scripts_dir.exists():
            continue

        override_data, user_data = build_data(chezmoi_root, os_name)

        for tmpl in sorted(scripts_dir.glob("*.sh.tmpl")):
            errors += render_and_check(tmpl, override_data, user_data, os_name, args.verbose)

        for sh in sorted(scripts_dir.glob("*.sh")):
            errors += run_shellcheck(sh, f"{os_name}/{sh.name}", override_data, user_data, args.verbose)

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


def render_and_check(tmpl: Path, override_data: dict, user_data: dict, os_name: str, verbose: bool) -> int:
    label = f"{os_name}/{tmpl.stem}"  # strip .tmpl
    merged = {**user_data, **override_data}
    try:
        result = subprocess.run(
            [
                "chezmoi", "execute-template",
                "--override-data", json.dumps(merged),
            ],
            stdin=tmpl.open(),
            capture_output=True,
            text=True,
        )
    except Exception as e:
        print(f"RENDER ERROR: {label}: {e}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(f"RENDER FAILED: {label}\n{result.stderr}", file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(result.stdout)
        tmp_path = f.name

    rc = run_shellcheck(tmp_path, label, override_data, user_data, verbose)
    if rc == 0:
        os.unlink(tmp_path)
    return rc


def run_shellcheck(path: str | Path, label: str, override_data: dict, user_data: dict, verbose: bool) -> int:
    if verbose:
        print_verbose(label, override_data, user_data)
    else:
        print(f"shellcheck: {label}")
    result = subprocess.run(["shellcheck", str(path)])
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    main()
