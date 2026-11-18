#!/usr/bin/env bash
# private-data-sync.sh — Keeps a gitignored plaintext copy of this machine class's
# private data (home/.private/<class>.yaml) in sync with its committed ciphertext
# (home/.private/<class>.yaml.age), so tools can read and edit it without decrypting.
#
# Sync is three-way against the last agreed content, recorded as a hash in
# home/.private/.<class>.yaml.base:
#   - plaintext missing or unedited, ciphertext changed  → decrypt into the plaintext
#   - plaintext edited, ciphertext unchanged             → re-encrypt into the ciphertext
#   - both changed                                       → conflict, touch nothing
# age output is randomized, so the ciphertext is rewritten only when the content changes.
#
# Usage:
#   private-data-sync.sh          sync (chezmoi read-source-state.pre hook); never fails
#   private-data-sync.sh --check  sync, then exit 1 if the ciphertext changed or a
#                                 conflict remains (pre-commit hook)
set -euo pipefail

check=false
[[ "${1:-}" == "--check" ]] && check=true

private_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../home/.private" && pwd)"
config="${XDG_CONFIG_HOME:-${HOME}/.config}/chezmoi/chezmoi.toml"

# Reads a string key from the [age] table of the generated chezmoi config.
age_value() {
    awk -v key="$1" '
        /^[[:space:]]*\[/ { in_age = ($0 ~ /^[[:space:]]*\[age\][[:space:]]*$/); next }
        in_age && $1 == key { sub(/^[^=]*=[[:space:]]*"/, ""); sub(/"[[:space:]]*$/, ""); print; exit }
    ' "${config}"
}

[[ -r "${config}" ]] || exit 0
identity="$(age_value identity)"
recipients="$(age_value recipientsFile)"
age_cmd="$(age_value command)"
age_cmd="${age_cmd:-age}"

# No age configured (headless without an identity): nothing to sync.
[[ -n "${identity}" && -s "${identity}" && -n "${recipients}" ]] || exit 0
command -v "${age_cmd}" >/dev/null 2>&1 || exit 0

class="$(basename "${recipients}" -recipient.txt)"
cipher="${private_dir}/${class}.yaml.age"
plain="${private_dir}/${class}.yaml"
base="${private_dir}/.${class}.yaml.base"
[[ -f "${cipher}" ]] || exit 0

sha() { shasum -a 256 | cut -d' ' -f1; }
fail() {
    echo "private-data-sync: $*" >&2
    if ${check}; then exit 1; fi
    exit 0
}

umask 077
if ! decrypted="$("${age_cmd}" -d -i "${identity}" "${cipher}")"; then
    fail "could not decrypt ${cipher}"
fi
cipher_sha="$(printf '%s\n' "${decrypted}" | sha)"
base_sha="$(cat "${base}" 2>/dev/null || true)"

if [[ ! -f "${plain}" ]]; then
    printf '%s\n' "${decrypted}" >"${plain}"
    echo "${cipher_sha}" >"${base}"
    exit 0
fi

plain_sha="$(sha <"${plain}")"

if [[ "${plain_sha}" == "${cipher_sha}" ]]; then
    [[ "${base_sha}" == "${cipher_sha}" ]] || echo "${cipher_sha}" >"${base}"
    exit 0
fi

if [[ "${plain_sha}" == "${base_sha}" ]]; then
    printf '%s\n' "${decrypted}" >"${plain}"
    echo "${cipher_sha}" >"${base}"
    exit 0
fi

if [[ "${cipher_sha}" == "${base_sha}" ]]; then
    tmp="$(mktemp "${cipher}.XXXXXX")"
    trap 'rm -f "${tmp}"' EXIT
    "${age_cmd}" -e -a -R "${recipients}" -o "${tmp}" "${plain}"
    mv "${tmp}" "${cipher}"
    echo "${plain_sha}" >"${base}"
    if ${check}; then
        echo "private-data-sync: re-encrypted ${class}.yaml into ${cipher}; stage it and commit again" >&2
        exit 1
    fi
    exit 0
fi

fail "conflict: ${plain} and ${cipher} both changed since the last sync.
  Merge the changes into ${plain}, then run:
    ${age_cmd} -e -a -R ${recipients} -o ${cipher} ${plain}"
