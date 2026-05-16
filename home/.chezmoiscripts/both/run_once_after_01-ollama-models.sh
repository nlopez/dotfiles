#!/usr/bin/env bash
# Auto-generate ~/.pi/agent/models.json from `ollama list`.
# Runs via chezmoi on every apply so newly pulled/removed models stay in sync
# without manual editing.  If ollama is not installed the file is left untouched.
set -euo pipefail

OUTPUT="$HOME/.pi/agent/models.json"

# If ollama CLI not available, skip silently.
if ! command -v ollama &>/dev/null; then
  echo "[ollama-models] ollama CLI not found — skipping"
  exit 0
fi

model_lines=$(ollama list 2>/dev/null | tail -n +2 || true)
model_count=$(echo "$model_lines" | grep -c . || true)
if [[ "$model_count" -eq 0 ]]; then
  echo "[ollama-models] ollama list returned 0 models — skipping"
  exit 0
fi

# --- helpers ---

is_qwen_family() {
  [[ "$1" == qwen3* ]]
}

is_gemma() {
  [[ "$1" == gemma* ]]
}

# --- build JSON ---

{
  echo '{'
  echo '   "providers": {'
  echo '      "ollama": {'
  echo '         "baseUrl": "http://localhost:11434/v1",'
  echo '         "api": "openai-completions",'
  echo '         "apiKey": "ollama",'
  echo '         "compat": {'
  echo '            "supportsDeveloperRole": false,'
  echo '            "supportsReasoningEffort": false'
  echo '         },'
  echo '         "models": ['

  idx=0
  total=$model_count
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    model_id="${line%% *}"
    [[ -z "$model_id" ]] && continue

    idx=$((idx + 1))

    # Open the object
    echo "         {"

    if is_qwen_family "$model_id"; then
      printf '            "id": "%s",\n'              "$model_id"
      echo '            "name": "'$model_id' (Local)",'
      echo '            "reasoning": true,'
      echo '            "compat": { "thinkingFormat": "qwen-chat-template" }'
    elif is_gemma "$model_id"; then
      printf '            "id": "%s",\n'              "$model_id"
      echo '            "name": "'$model_id' (Local)",'
      echo '            "input": ["text", "image"]'
    else
      printf '            "id": "%s",\n'              "$model_id"
      echo '            "name": "'$model_id' (Local)"'
    fi

    if [[ "$idx" -lt "$total" ]]; then
      echo '         },'
    else
      echo '         }'
    fi
  done <<< "$model_lines"

  echo ''
  echo '       ]'
  echo '      }'
  echo '   }'
  echo '}'
} > "$OUTPUT"

echo "[ollama-models] wrote $model_count models to $OUTPUT"
