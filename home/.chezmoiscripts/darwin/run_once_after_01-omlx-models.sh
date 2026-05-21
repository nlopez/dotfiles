#!/usr/bin/env bash
# Generate ~/.pi/agent/models.json for omlx (OpenAI-compatible server at :8000).
# The model list is the source of truth — taken from chezmoi data
# (home/.chezmoidata/omlx.yaml), not discovered from the filesystem.
# Skips silently if omlx or chezmoi is not available.

OMLX_API_URL="http://localhost:8000/v1"
OUTPUT="$HOME/.pi/agent/models.json"
MODEL_DIR="$HOME/.omlx/models"
OMLX_SETTINGS="$HOME/.omlx/settings.json"
CHEZMOI_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

if ! command -v omlx &>/dev/null; then
  echo "[omlx-models] omlx CLI not found — skipping"
  exit 0
fi

# ------------------------------------------------------------------
# Fetch model list: try chezmoi data (source of truth).
# If not available, fall back to filesystem discovery.
# ------------------------------------------------------------------
MODEL_LIST_JSON=""

# Try chezmoi data first (authoritative list)
if command -v chezmoi &>/dev/null; then
  MODEL_LIST_JSON=$(cd "$CHEZMOI_ROOT" && chezmoi data 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = data.get('omlx', {}).get('models', [])
if models:
    print(json.dumps(models))
else:
    sys.exit(1)
" 2>/dev/null)
fi

# Fallback: discover from filesystem
if [[ -z "$MODEL_LIST_JSON" ]]; then
  if [[ -d "$MODEL_DIR" ]]; then
    MODEL_LIST_JSON=$(python3 -c "
import json, os
model_dir = '$MODEL_DIR'
models = []
for entry in sorted(os.listdir(model_dir)):
    cfg = os.path.join(model_dir, entry, 'config.json')
    if os.path.isfile(cfg):
        models.append({'id': entry, 'name': entry})
if models:
    print(json.dumps(models))
" 2>/dev/null)
  fi
fi

if [[ -z "$MODEL_LIST_JSON" ]]; then
  echo "[omlx-models] no models found — skipping"
  exit 0
fi

# ------------------------------------------------------------------
# Read sampling config from chezmoi data (source of truth).
# Used as default contextWindow/maxTokens for all models,
# with per-model override support via the model entry.
# ------------------------------------------------------------------
SAMPLE_JSON=""
if command -v chezmoi &>/dev/null; then
  SAMPLE_JSON=$(cd "$CHEZMOI_ROOT" && chezmoi data 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
sampling = data.get('omlx', {}).get('sampling', {})
if sampling:
    print(json.dumps(sampling))
else:
    print('{}')
" 2>/dev/null)
fi
if [[ -z "$SAMPLE_JSON" ]]; then
  SAMPLE_JSON='{"max_context_window": 131072, "max_tokens": 131072}'
fi

# ------------------------------------------------------------------
# Read API key from omlx settings (if available)
# ------------------------------------------------------------------
api_key="omlx"
if [[ -f "$OMLX_SETTINGS" ]]; then
  api_key=$(python3 -c "
import json, sys
try:
    with open('$OMLX_SETTINGS') as f:
        settings = json.load(f)
    print(settings.get('auth', {}).get('api_key', 'omlx'))
except Exception:
    print('omlx')
" 2>/dev/null)
fi

# ------------------------------------------------------------------
# Build the final models.json using Python for correctness.
# ------------------------------------------------------------------
python3 - "$OMLX_API_URL" "$OUTPUT" "$api_key" "$MODEL_LIST_JSON" "$SAMPLE_JSON" <<'PYEOF'
import json, os, sys

api_url = sys.argv[1]
output_path = sys.argv[2]
api_key = sys.argv[3]
model_list_raw = sys.argv[4]
sampling_raw = sys.argv[5]

models = json.loads(model_list_raw)

# Read sampling config (applied as defaults, with per-model override support)
sampling = json.loads(sampling_raw)

# Ensure all models have the expected structure
formatted_models = []
for m in models:
    entry = {
        "id": m["id"],
        "name": m.get("name", m["id"]) + " (Local)",
    }
    # Copy reasoning flag
    entry["reasoning"] = m.get("reasoning", False)
    # Copy input types
    entry["input"] = m.get("input", ["text"])
    # Copy compat if present
    if "compat" in m:
        entry["compat"] = m["compat"]
    # Copy modelType if present (e.g. "ocr")
    if "modelType" in m:
        entry["modelType"] = m["modelType"]

    # Apply default contextWindow/maxTokens from sampling config
    # (allow per-model overrides in the model entry)
    entry["contextWindow"] = m.get("contextWindow", sampling.get("max_context_window", 131072))
    entry["maxTokens"] = m.get("maxTokens", sampling.get("max_tokens", 131072))

    formatted_models.append(entry)

# --- Write output ---
output = {
    "providers": {
        "omlx": {
            "baseUrl": api_url,
            "api": "openai-completions",
            "apiKey": api_key,
            "authHeader": True,
            "models": formatted_models,
        }
    }
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
    f.write("\n")

print(f"[omlx-models] wrote {len(formatted_models)} models from chezmoi data to {output_path}")
PYEOF
