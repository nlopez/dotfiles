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
#   SA_TOKEN_OP_URI     1Password secret reference for the Automation service-account
#                       token (personal macOS only; fetched via app auth on first run)
set -euo pipefail

IDENTITY_DIR="${HOME}/.local/share/chezmoi-age"
IDENTITY_FILE="${IDENTITY_DIR}/identity.txt"
KEYCHAIN_SERVICE="chezmoi-age-identity"
TOKEN_ITEM="op-service-account-automation"

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

keychain_token() {
    security find-generic-password -a "${USER}" -s "${TOKEN_ITEM}" -w 2>/dev/null || true
}

keychain_store_token() {
    local token="$1"
    [[ -n "${token}" ]] || return 1
    printf 'add-generic-password -U -a "%s" -s "%s" -w "%s"\n' "${USER}" "${TOKEN_ITEM}" "${token}" |
        security -i >/dev/null
}

# The CLI normally arrives with the Nix profile, which only exists after this
# hook has produced the age key, so install it here on first run.
ensure_op() {
    for dir in /opt/homebrew/bin /usr/local/bin; do
        if [[ -x "${dir}/op" ]] && [[ ":${PATH}:" != *":${dir}:"* ]]; then
            export PATH="${dir}:${PATH}"
        fi
    done
    command -v op >/dev/null && return 0
    if [[ -n "${IN_WORKSPACE:-}" ]]; then
        echo "fetch-age-key: workspace machine, not installing the 1Password CLI" >&2
        fetch_failed
    fi
    bash "$(dirname "$0")/install-op.sh"
    for dir in /opt/homebrew/bin /usr/local/bin; do
        if [[ -x "${dir}/op" ]] && [[ ":${PATH}:" != *":${dir}:"* ]]; then
            export PATH="${dir}:${PATH}"
        fi
    done
}

# Populated once per personal Mac; the read-only service account keeps later
# reads promptless. Tries Keychain -> env var -> 1Password app auth -> paste.
ensure_token() {
    [[ -n "$(keychain_token)" ]] && return 0

    if [[ -n "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
        keychain_store_token "${OP_SERVICE_ACCOUNT_TOKEN}"
        echo "fetch-age-key: stored service-account token in the Keychain (${TOKEN_ITEM})" >&2
        return 0
    fi

    local token=""
    if [[ -n "${SA_TOKEN_OP_URI:-}" ]]; then
        echo "fetch-age-key: reading service-account token from 1Password (${SA_TOKEN_OP_URI})..." >&2
        token="$(OP_APP_AUTH=1 op read --no-newline "${SA_TOKEN_OP_URI}" || true)"
        if [[ -n "${token}" ]]; then
            keychain_store_token "${token}"
            echo "fetch-age-key: stored service-account token in the Keychain (${TOKEN_ITEM})" >&2
            return 0
        fi
    fi

    [[ -t 0 ]] || return 1
    echo "fetch-age-key: paste the 1Password service-account token for the Automation vault (input hidden):" >&2
    read -rs token
    echo >&2
    keychain_store_token "${token}"
}

ensure_op

if [[ "$(uname -s)" == "Darwin" ]]; then
    if [[ -n "${SA_TOKEN_OP_URI:-}" ]]; then
        ensure_token || fetch_failed
        OP_SERVICE_ACCOUNT_TOKEN="$(keychain_token)" op read --no-newline "${AGE_KEY_OP_URI}" |
            keychain_store || fetch_failed
    else
        op read --no-newline "${AGE_KEY_OP_URI}" | keychain_store || fetch_failed
    fi
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
