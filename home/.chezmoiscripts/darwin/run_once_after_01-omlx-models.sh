#!/usr/bin/env bash
# Leave models.json empty — omlx models are auto-discovered via the
# local-models extension (see home/dot_pi/agent/extensions/local-models/).
# The extension probes the omlx API and registers models dynamically.
# Skips silently if Pi is not available.

OUTPUT="$HOME/.pi/agent/models.json"

# Ensure the output directory exists
mkdir -p "$(dirname "$OUTPUT")"

# Write empty config — the local-models extension will auto-discover models
printf '{}\n' > "$OUTPUT"

echo "[omlx-models] models.json left empty for auto-discovery via local-models extension"
