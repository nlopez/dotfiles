#!/usr/bin/env bash
# op-automation.sh — Runs `op` authenticated as the read-only service account
# for the Automation vault, so reads never prompt. Lives in scripts/ so chezmoi
# templates can invoke it during the very first `chezmoi init --apply` before
# ~/.local/bin/op-automation exists.
set -euo pipefail

if ! command -v op >/dev/null 2>&1; then
    for dir in /opt/homebrew/bin /usr/local/bin; do
        if [[ -x "${dir}/op" ]]; then
            export PATH="${dir}:${PATH}"
            break
        fi
    done
fi

OP_SERVICE_ACCOUNT_TOKEN=$(security find-generic-password -a "${USER}" -s op-service-account-automation -w) || {
    echo "op-automation: Keychain item op-service-account-automation not found" >&2
    exit 1
}
export OP_SERVICE_ACCOUNT_TOKEN
exec op "$@"
