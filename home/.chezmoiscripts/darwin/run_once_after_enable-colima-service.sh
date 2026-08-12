#!/bin/bash
# Enable colima as a login-item launchd service so it starts automatically at login.
# brew services start loads the plist (RunAtLoad: true, KeepAlive: SuccessfulExit).
set -eufo pipefail

brew services start colima
