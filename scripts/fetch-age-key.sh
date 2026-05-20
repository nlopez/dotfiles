#!/usr/bin/env bash
# fetch-age-key.sh — Fetches the age private key from 1Password and writes it to the
# chezmoi-age identity file. Called via hooks.read-source-state.pre so that the key is
# available before chezmoi reads (and therefore needs to decrypt) any source files.
#
# Environment variables injected by chezmoi [scriptEnv] in chezmoi.toml:
#   AGE_KEY_OP_URI      1Password secret reference, e.g. op://Private/age-key/private-key
#   AGE_KEY_OP_ACCOUNT  1Password account URL, e.g. datadog.1password.com
#
# The identity file is left on disk between chezmoi runs (no post-hook cleanup).
# The directory is created with mode 700; the identity file is created with mode 600.
set -euo pipefail

IDENTITY_DIR="${HOME}/.local/share/chezmoi-age"
IDENTITY_FILE="${IDENTITY_DIR}/identity.txt"

# Fast path: key already present — skip 1Password entirely.
if [[ -s "${IDENTITY_FILE}" ]]; then
    exit 0
fi

# If env vars are absent this machine has no age encryption configured (e.g. headless/ephemeral).
# Warn but do not fail so chezmoi continues normally.
if [[ -z "${AGE_KEY_OP_URI:-}" ]] || [[ -z "${AGE_KEY_OP_ACCOUNT:-}" ]]; then
    echo "fetch-age-key: AGE_KEY_OP_URI or AGE_KEY_OP_ACCOUNT not set — skipping age key fetch" >&2
    exit 0
fi

# Create the identity directory with restricted permissions.
(umask 077 && mkdir -p "${IDENTITY_DIR}")

# Write to a temp file first so the move into place is atomic.
TMPFILE="$(mktemp "${IDENTITY_DIR}/.identity.tmp.XXXXXX")"
trap 'rm -f "${TMPFILE}"' EXIT

if ! op read --no-newline \
    --account "${AGE_KEY_OP_ACCOUNT}" \
    "${AGE_KEY_OP_URI}" > "${TMPFILE}" 2>&1; then
    echo "fetch-age-key: WARNING — could not fetch age key from 1Password (${AGE_KEY_OP_URI})" >&2
    echo "  Run: op read --account ${AGE_KEY_OP_ACCOUNT} '${AGE_KEY_OP_URI}'" >&2
    echo "  chezmoi will fail if it encounters encrypted source files." >&2
    exit 0
fi

chmod 600 "${TMPFILE}"
mv "${TMPFILE}" "${IDENTITY_FILE}"

echo "fetch-age-key: wrote age identity to ${IDENTITY_FILE}" >&2
