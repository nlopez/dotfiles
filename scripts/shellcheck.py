#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from chezmoi_lib import OSES, build_data, chezmoi_root, print_verbose, render_template


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render chezmoi templates and shellcheck .sh files"
    )
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

        override_data, user_data = build_data(root, os_name)

        for tmpl in sorted(scripts_dir.glob("*.sh.tmpl")):
            errors += render_and_check(
                tmpl, override_data, user_data, os_name, args.verbose
            )

        for sh in sorted(scripts_dir.glob("*.sh")):
            errors += run_shellcheck(
                sh, f"{os_name}/{sh.name}", override_data, user_data, args.verbose
            )

    if errors:
        print(f"\n{errors} error(s)", file=sys.stderr)
        sys.exit(1)
    print("\nAll checks passed.")


def render_and_check(
    tmpl: Path, override_data: dict, user_data: dict, os_name: str, verbose: bool
) -> int:
    label = f"{os_name}/{tmpl.stem}"  # strip .tmpl

    output, error = render_template(tmpl, override_data, user_data)
    if error:
        print(f"RENDER FAILED: {label}\n{error}", file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(output)
        tmp_path = f.name

    rc = run_shellcheck(tmp_path, label, override_data, user_data, verbose)
    if rc == 0:
        os.unlink(tmp_path)
    return rc


def run_shellcheck(
    path: str | Path, label: str, override_data: dict, user_data: dict, verbose: bool
) -> int:
    if verbose:
        print_verbose(label, override_data, user_data)
    else:
        print(f"shellcheck: {label}")
    result = subprocess.run(["shellcheck", str(path)])
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    main()
