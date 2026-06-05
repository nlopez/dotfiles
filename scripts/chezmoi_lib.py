#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import json
import subprocess
from pathlib import Path

import yaml

OSES = ["darwin", "linux", "linux-debian", "windows"]


def chezmoi_root() -> Path:
    return Path(subprocess.check_output(["chezmoi", "source-path"]).decode().strip())


def build_data(root: Path, os_name: str) -> dict:
    """Build override and user data for template rendering."""
    # linux-debian targets Ubuntu/Debian; chezmoi.os must be "linux" with a
    # non-aurora osRelease so the .chezmoiignore gates fire correctly.
    effective_os = "linux" if os_name == "linux-debian" else os_name
    override_data = {
        "chezmoi": {
            "os": effective_os,
            "osRelease": {
                "id": "ubuntu",
                "ubuntuCodename": "noble",
            },
        },
    }

    user_data = {
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

    return {**override_data, **user_data}


def render_template(tmpl: Path, data: dict) -> tuple[str | None, str | None]:
    """Render a chezmoi template file, returning (output, error)."""
    result = subprocess.run(
        [
            "chezmoi",
            "execute-template",
            "--file",
            "--override-data",
            json.dumps(data),
            str(tmpl),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout, None


def print_verbose(label: str, os_name: str, user_data: dict) -> None:
    """Print verbose output with OS and user configuration."""
    vars_str = " ".join(
        f"{k}={json.dumps(v)}"
        for k, v in {**{"chezmoi.os": os_name}, **{k: v for k, v in user_data.items() if k != "packages"}.items()}
    )
    print(f"{label} [{vars_str}]")
