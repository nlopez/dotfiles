#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from chezmoi_lib import OSES, build_data, chezmoi_root, print_verbose, render_template


def main() -> None:
    parser = argparse.ArgumentParser(description="Render chezmoi templates and shellcheck .sh files")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print filename and variable inputs for each check",
    )
    args = parser.parse_args()

    root = chezmoi_root()
    errors = 0

    for os_name in OSES:
        scripts_dir = root / ".chezmoiscripts" / os_name
        if not scripts_dir.exists():
            continue

        data = build_data(root, os_name)

        for tmpl in sorted(scripts_dir.glob("*.sh.tmpl")):
            errors += render_and_check(tmpl, data, os_name, args.verbose)

        for sh in sorted(scripts_dir.glob("*.sh")):
            errors += run_shellcheck(sh, f"{os_name}/{sh.name}", data, args.verbose)

    if errors:
        print(f"\n{errors} error(s)", file=sys.stderr)
        sys.exit(1)
    print("\nAll checks passed.")


def render_and_check(tmpl: Path, data: dict, os_name: str, verbose: bool) -> int:
    label = f"{os_name}/{tmpl.stem}"  # strip .tmpl

    output, error = render_template(tmpl, data)
    if error is not None or output is None:
        print(f"RENDER FAILED: {label}\n{error}", file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(output)
        tmp_path = f.name

    rc = run_shellcheck(tmp_path, label, data, verbose)
    if rc == 0:
        os.unlink(tmp_path)
    return rc


def run_shellcheck(path: str | Path, label: str, data: dict, verbose: bool) -> int:
    if verbose:
        print_verbose(label, data["chezmoi"]["os"], data)
    else:
        print(f"shellcheck: {label}")
    result = subprocess.run(["shellcheck", str(path)])
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    main()
