#!/usr/bin/env bash
set -euo pipefail

readonly USER_DATA_HOME="${XDG_DATA_HOME:-${HOME:?HOME must be set}/.local/share}"
readonly DEFAULT_BIOS_DIR="${PCE_BIOS_DIR:-${USER_DATA_HOME}/pce-development/bios}"

if [[ -z "${PCE_SYSTEM_CARD_BIOS:-}" ]]; then
    mkdir -p -- "$DEFAULT_BIOS_DIR"
    printf 'CD-ROM² emulation needs an extracted System Card BIOS (.pce). Place it in %s, then set PCE_SYSTEM_CARD_BIOS to its full file path. The BIOS is not included in the project.\n' "$DEFAULT_BIOS_DIR" >&2
    exit 2
fi

if [[ ! -f "$PCE_SYSTEM_CARD_BIOS" || ! -r "$PCE_SYSTEM_CARD_BIOS" ]]; then
    printf 'Configured System Card BIOS is missing or unreadable: %s\n' "$PCE_SYSTEM_CARD_BIOS" >&2
    printf 'Place the extracted BIOS in %s or update PCE_SYSTEM_CARD_BIOS to its full file path.\n' "$(dirname -- "$PCE_SYSTEM_CARD_BIOS")" >&2
    exit 2
fi

printf '%s\n' "$PCE_SYSTEM_CARD_BIOS"
