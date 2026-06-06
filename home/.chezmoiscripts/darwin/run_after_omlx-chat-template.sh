#!/usr/bin/env bash
# Copy the Qwen fixed chat template (froggeric v20) into every Qwen model
# directory under ~/.local/share/omlx/models/.
#
# Triggered by run_after_* — runs every chezmoi apply so that:
#   • New Qwen models picked up by omlx get the template immediately
#   • Re-downloaded models (which restore the original template) are fixed
#
# Source of truth: ~/.omlx/chat_template.jinja (managed by chezmoi)

SOURCE="$HOME/.omlx/chat_template.jinja"
MODEL_BASE="$HOME/.local/share/omlx/models"

[[ ! -f "$SOURCE" ]] && exit 0
[[ ! -d "$MODEL_BASE" ]] && exit 0

count=0
while IFS= read -r config; do
    model_dir="$(dirname "$config")"
    dest="$model_dir/chat_template.jinja"

    if [[ -f "$dest" ]]; then
        current_version="$(grep 'template_version' "$dest" 2>/dev/null | head -1)"
        if [[ "$current_version" == *"froggeric-v20"* ]]; then
            continue
        fi
        # Back up the original only once
        [[ ! -f "${dest}.original" ]] && cp "$dest" "${dest}.original"
    fi

    cp "$SOURCE" "$dest"
    echo "[omlx-chat-template] updated $model_dir"
    count=$((count + 1))
done < <(find "$MODEL_BASE" -name "config.json" -exec grep -l '"Qwen3_' {} \; 2>/dev/null)

echo "[omlx-chat-template] done — $count model(s) updated (source: $SOURCE)"
