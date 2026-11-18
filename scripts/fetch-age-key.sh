#!/usr/bin/env bash
# fetch-age-key.sh — Fetches the age private key from 1Password before chezmoi reads
# (and therefore decrypts) source files. Called via hooks.read-source-state.pre.
#
# macOS: stores the key in the login Keychain (service chezmoi-age-identity), where
# age-keychain.sh reads it through varlock. Nothing is written to disk, and an
# identity file left by an earlier setup is moved into the Keychain and deleted.
# Other platforms: writes the identity file (mode 600 in a mode 700 directory).
#
# Environment variables injected by chezmoi [scriptEnv] in chezmoi.toml:
#   AGE_KEY_OP_URI      1Password secret reference, e.g. op://vault/item/private-key
set -euo pipefail

IDENTITY_DIR="${HOME}/.local/share/chezmoi-age"
IDENTITY_FILE="${IDENTITY_DIR}/identity.txt"
KEYCHAIN_SERVICE="chezmoi-age-identity"

keychain_store() {
    local key
    key="$(grep '^AGE-SECRET-KEY-' || true)"
    if [[ -z "${key}" ]]; then
        echo "fetch-age-key: no AGE-SECRET-KEY line in the fetched identity" >&2
        return 1
    fi
    # security -i reads the command from stdin, so the key never appears in ps output.
    printf 'add-generic-password -U -a "%s" -s "%s" -w "%s"\n' "${USER}" "${KEYCHAIN_SERVICE}" "${key}" |
        security -i >/dev/null
}

if [[ "$(uname -s)" == "Darwin" ]]; then
    if security find-generic-password -s "${KEYCHAIN_SERVICE}" >/dev/null 2>&1; then
        rm -f "${IDENTITY_FILE}"
        exit 0
    fi
    if [[ -s "${IDENTITY_FILE}" ]]; then
        keychain_store <"${IDENTITY_FILE}"
        rm -f "${IDENTITY_FILE}"
        echo "fetch-age-key: moved ${IDENTITY_FILE} into the Keychain" >&2
        exit 0
    fi
elif [[ -s "${IDENTITY_FILE}" ]]; then
    exit 0
fi

# chezmoi-fast (CHEZMOI_SKIP_SECRETS=1): never touch 1Password.
if [[ -n "${CHEZMOI_SKIP_SECRETS:-}" ]]; then
    exit 0
fi

# If AGE_KEY_OP_URI is absent this machine has no age key configured
# (e.g. headless/ephemeral machines). Warn but do not fail so chezmoi
# continues normally.
if [[ -z "${AGE_KEY_OP_URI:-}" ]]; then
    echo "fetch-age-key: AGE_KEY_OP_URI not set — skipping age key fetch" >&2
    exit 0
fi

fetch_failed() {
    echo "fetch-age-key: WARNING — could not fetch age key from 1Password (${AGE_KEY_OP_URI})" >&2
    echo "  Run: op read '${AGE_KEY_OP_URI}'" >&2
    echo "  chezmoi will fail if it encounters encrypted source files." >&2
    exit 0
}

if [[ "$(uname -s)" == "Darwin" ]]; then
    op read --no-newline "${AGE_KEY_OP_URI}" | keychain_store || fetch_failed
    echo "fetch-age-key: stored age identity in the Keychain (${KEYCHAIN_SERVICE})" >&2
    exit 0
fi

(umask 077 && mkdir -p "${IDENTITY_DIR}")

# Write to a temp file first so the move into place is atomic.
TMPFILE="$(mktemp "${IDENTITY_DIR}/.identity.tmp.XXXXXX")"
trap 'rm -f "${TMPFILE}"' EXIT

op read --no-newline "${AGE_KEY_OP_URI}" >"${TMPFILE}" 2>/dev/null || fetch_failed

chmod 600 "${TMPFILE}"
mv "${TMPFILE}" "${IDENTITY_FILE}"

echo "fetch-age-key: wrote age identity to ${IDENTITY_FILE}" >&2
