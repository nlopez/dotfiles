#!/bin/bash
# Update pi-coding-agent to the latest version via npm.
# Run: update-pi-agent
# Or:  update-pi-agent <version>  (e.g., update-pi-agent 1.0.0)

VERSION="${1:-latest}"
echo "Updating pi-coding-agent to ${VERSION}..."
npm install -g @earendil-works/pi-coding-agent@"${VERSION}"
echo ""
echo "Installed: $(pi --version 2>/dev/null || echo 'unknown')"
