#!/usr/bin/env python3
"""Sets 🛎️ when Claude needs attention.
Hooked on Notification[idle_prompt|permission_prompt].
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
    ["tmux", "set-option", "-w", "-t", pane, "@pi-status", "🛎️ "],
    capture_output=True,
)
