#!/usr/bin/env python3
"""Sets 🤖 on the tmux window while Claude is processing.
Hooked on UserPromptSubmit and PostToolUse[.*].
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
    ["tmux", "set-option", "-w", "-t", pane, "@pi-status", "🤖 "],
    capture_output=True,
)
