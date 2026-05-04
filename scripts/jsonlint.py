#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import json5
from chezmoi_lib import OSES, build_data, chezmoi_root, print_verbose, render_template


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

    root = chezmoi_root()
    errors = 0

    # Lint plain .json files (no templating needed)
    for json_file in sorted(root.rglob("*.json")):
        content = json_file.read_text()
        if "chezmoi:modify-template" in content:
            continue
        errors += lint_json(
            content,
            str(json_file.relative_to(root)),
            args.verbose,
        )

    # Render and lint .json.tmpl files for each OS
    for os_name in OSES:
        override_data, user_data = build_data(root, os_name)

        for tmpl in sorted(root.rglob("*.json.tmpl")):
            # modify_*.json.tmpl files are chezmoi modify-scripts (shell), not JSON.
            if tmpl.name.startswith("modify_"):
                continue
            label = f"{os_name}/{tmpl.relative_to(root)}"
            errors += render_and_lint(
                tmpl, override_data, user_data, label, args.verbose
            )

    if errors:
        print(f"\n{errors} error(s)", file=sys.stderr)
        sys.exit(1)
    print("\nAll checks passed.")


def render_and_lint(
    tmpl: Path, override_data: dict, user_data: dict, label: str, verbose: bool
) -> int:
    if verbose:
        print_verbose(label, override_data, user_data)
    else:
        print(f"jsonlint: {label}")

    output, error = render_template(tmpl, override_data, user_data)
    if error is not None or output is None:
        print(f"RENDER FAILED: {label}\n{error}", file=sys.stderr)
        return 1

    return lint_json(output, label, verbose)


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
