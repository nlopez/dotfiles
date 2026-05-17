#!/usr/bin/env bash
# Generate ~/.pi/agent/models.json for omlx (OpenAI-compatible server at :8000).
# Since omlx has no `omlx list` CLI, we query its REST API.
# Falls back to a curated mlx-community list when the server is not running.
# Skips silently if omlx is not installed yet.

OMLX_API_URL="http://localhost:8000/v1"
OUTPUT="$HOME/.pi/agent/models.json"

if ! command -v omlx &>/dev/null; then
  echo "[omlx-models] omlx CLI not found — skipping"
  exit 0
fi

# ------------------------------------------------------------------
# Fetch model IDs: try the live server first, fall back to defaults.
# ------------------------------------------------------------------
FALLBACK_MODELS=(
  "mlx-community/Qwen3.5-35B-A3B-4bit"
  "mlx-community/Qwen3.5-35B-A3B-coder-4bit"
  "mlx-community/Llama-4-Scout-35B-A3B-FP8"
)

model_ids=$(python3 - <<'PYEOF' 2>/dev/null
import json, urllib.request, urllib.error, sys

url = "http://localhost:8000/v1/models"
try:
    with urllib.request.urlopen(url, timeout=2) as r:
        data = json.loads(r.read())
    ids = [m["id"] for m in data.get("data", [])]
    if ids:
        print("\n".join(ids))
        sys.exit(0)
except Exception:
    pass
sys.exit(1)
PYEOF
)

if [[ -z "$model_ids" ]]; then
  model_ids=$(printf '%s\n' "${FALLBACK_MODELS[@]}")
fi

model_count=$(printf '%s\n' "$model_ids" | grep -c .) || true
if [[ "$model_count" -eq 0 ]]; then
  echo "[omlx-models] no models found — skipping"
  exit 0
fi

# ------------------------------------------------------------------
# Build JSON.
# ------------------------------------------------------------------
is_qwen() { [[ "$1" == *qwen* || "$1" == *Qwen* ]]; }
is_gemma() { [[ "$1" == *gemma* || "$1" == *Gemma* ]]; }

{
  printf '{\n'
  printf '  "providers": {\n'
  printf '    "omlx": {\n'
  printf '      "baseUrl": "%s",\n' "$OMLX_API_URL"
  printf '      "api": "openai-completions",\n'
  printf '      "apiKey": "omlx",\n'
  printf '      "compat": {\n'
  printf '        "supportsDeveloperRole": false,\n'
  printf '        "supportsReasoningEffort": false\n'
  printf '      },\n'
  printf '      "models": [\n'

  idx=0
  while IFS= read -r model; do
    [[ -z "$model" ]] && continue
    idx=$((idx + 1))

    printf '        {\n'
    printf '          "id": "%s",\n' "$model"
    printf '          "name": "%s (Local)"' "$model"

    if is_qwen "$model"; then
      printf ',\n          "reasoning": true,\n'
      printf '          "compat": { "thinkingFormat": "qwen-chat-template" }\n'
    elif is_gemma "$model"; then
      printf ',\n          "input": ["text", "image"]\n'
    else
      printf '\n'
    fi

    if [[ "$idx" -lt "$model_count" ]]; then
      printf '        },\n'
    else
      printf '        }\n'
    fi
  done <<< "$model_ids"

  printf '      ]\n'
  printf '    }\n'
  printf '  }\n'
  printf '}\n'
} > "$OUTPUT"

echo "[omlx-models] wrote $model_count models to $OUTPUT"
