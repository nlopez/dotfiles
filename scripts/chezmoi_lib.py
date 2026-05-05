#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import json
import subprocess
from pathlib import Path

import yaml

OSES = ["darwin", "linux", "windows"]


def chezmoi_root() -> Path:
    return Path(subprocess.check_output(["chezmoi", "source-path"]).decode().strip())


def build_data(root: Path, os_name: str) -> tuple[dict, dict]:
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

    pkg_file = root / ".chezmoidata" / os_name / "packages.yaml"
    if pkg_file.exists():
        with open(pkg_file) as f:
            user_data.update(yaml.safe_load(f))

    return override_data, user_data


def render_template(
    tmpl: Path, override_data: dict, user_data: dict
) -> tuple[str | None, str | None]:
    """Render a chezmoi template file, returning (output, error). One will always be None."""
    merged = {**user_data, **override_data}
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
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout, None


def print_verbose(label: str, override_data: dict, user_data: dict) -> None:
    chezmoi = override_data["chezmoi"]
    vars_: dict = {"chezmoi.os": chezmoi["os"]}
    vars_.update({k: v for k, v in user_data.items() if k != "packages"})
    vars_str = "  ".join(f"{k}={json.dumps(v)}" for k, v in vars_.items())
    print(f"  {label}  [{vars_str}]")
