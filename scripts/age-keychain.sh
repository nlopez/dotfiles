#!/usr/bin/env bash
# age-keychain.sh — chezmoi's [age] command on macOS. Runs the real age, and for
# decryption supplies the identity from the Keychain through `varlock run`
# (chezmoi-age.env) as an anonymous pipe, so the key never touches the disk.
# Falls back to reading the Keychain directly until mise has installed varlock.
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
real_age="$(command -v age)" || real_age="${HOME}/.local/state/nix/profiles/dotfiles/bin/age"

decrypt=false
for arg in "$@"; do
    case "${arg}" in -d | --decrypt) decrypt=true ;; esac
done
if ! ${decrypt}; then
    exec "${real_age}" "$@"
fi

if [[ -z "${CHEZMOI_AGE_IDENTITY:-}" ]]; then
    varlock="${XDG_DATA_HOME:-${HOME}/.local/share}/mise/shims/varlock"
    if [[ -x "${varlock}" ]]; then
        exec "${varlock}" run -p "${dir}/chezmoi-age.env" --filter CHEZMOI_AGE_IDENTITY \
            --inject vars --no-redact-stdout -- "${BASH_SOURCE[0]}" "$@"
    fi
    CHEZMOI_AGE_IDENTITY="$(security find-generic-password -s chezmoi-age-identity -w)"
fi

identity="${CHEZMOI_AGE_IDENTITY}"
unset CHEZMOI_AGE_IDENTITY
exec "${real_age}" "$@" --identity <(printf '%s\n' "${identity}")
