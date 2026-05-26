#!/usr/bin/env python3
"""Clears @pi-status when the Claude session ends.
Hooked on SessionEnd (fires on all exit reasons).
The Claude shim also clears it after process exit to handle crashes/SIGKILL.
"""

import os
import subprocess
import sys

if not os.environ.get("TMUX"):
    sys.exit(0)

pane = os.environ.get("TMUX_PANE", "")
if not pane:
    sys.exit(0)

subprocess.run(
    ["tmux", "set-option", "-wu", "-t", pane, "@pi-status"],
    capture_output=True,
)
