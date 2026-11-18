#!/usr/bin/env bash
# read-source-state-pre.sh — chezmoi hooks.read-source-state.pre: fetches the age
# identity from 1Password (machines with AGE_KEY_OP_URI), then syncs the plaintext
# private data copy with its ciphertext.
set -euo pipefail

dir="$(dirname "${BASH_SOURCE[0]}")"
if [[ -n "${AGE_KEY_OP_URI:-}" ]]; then
    bash "${dir}/fetch-age-key.sh"
fi
bash "${dir}/private-data-sync.sh"
