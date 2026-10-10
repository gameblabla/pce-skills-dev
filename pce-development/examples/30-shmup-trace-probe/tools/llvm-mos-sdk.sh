#!/usr/bin/env bash
set -euo pipefail

readonly SDK_VERSION=23.2.0
readonly SDK_URL="https://github.com/llvm-mos/llvm-mos-sdk/releases/download/v${SDK_VERSION}/llvm-mos-linux.tar.xz"
readonly SDK_SHA256=4d6c9f1833666261a3178906cef11d9544b0f3a8c238f9c288073a8055ae9e61
readonly SDK_COMPILER="${LLVM_MOS_CC:-mos-pce-clang}"
readonly SDK_COMPILER_NAME="${SDK_COMPILER##*/}"
readonly USER_DATA_HOME="${XDG_DATA_HOME:-${HOME:?HOME must be set}/.local/share}"
readonly USER_CACHE_HOME="${XDG_CACHE_HOME:-${HOME:?HOME must be set}/.cache}"
readonly SDK_ROOT="${PCE_LLVM_MOS_SDK_ROOT:-${USER_DATA_HOME}/pce-development/toolchains/llvm-mos-sdk/${SDK_VERSION}}"
readonly DOWNLOAD_DIR="${PCE_LLVM_MOS_DOWNLOAD_DIR:-${USER_CACHE_HOME}/pce-development/downloads}"
readonly ARCHIVE="${DOWNLOAD_DIR}/llvm-mos-linux-v${SDK_VERSION}.tar.xz"

error() {
    printf 'llvm-mos-sdk: %s\n' "$*" >&2
}

archive_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -- "$1" | awk '{ print $1 }'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 -- "$1" | awk '{ print $1 }'
    else
        error 'sha256sum or shasum is required to verify the SDK archive.'
        return 1
    fi
}

archive_is_valid() {
    local actual
    [[ -s "$1" ]] || return 1
    xz -t -- "$1" >/dev/null 2>&1 || return 1
    actual="$(archive_sha256 "$1")" || return 1
    [[ "$actual" == "$SDK_SHA256" ]]
}

resolved_bin_dir() {
    local candidate="$1"

    [[ -x "$candidate" ]] || return 1
    while [[ -L "$candidate" ]]; do
        local target
        target="$(readlink -- "$candidate")"
        if [[ "$target" = /* ]]; then
            candidate="$target"
        else
            candidate="$(dirname -- "$candidate")/$target"
        fi
    done
    candidate="$(cd -P -- "$(dirname -- "$candidate")" && pwd)/$(basename -- "$candidate")"
    dirname -- "$candidate"
}

path_compiler_bin() {
    local found
    found="$(command -v -- "$SDK_COMPILER" 2>/dev/null || true)"
    [[ -n "$found" ]] || return 1
    resolved_bin_dir "$found"
}

require_supported_host() {
    if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
        error 'the automatic release download supports Linux x86_64; install a matching LLVM-MOS PCE SDK and put mos-pce-clang on PATH.'
        return 1
    fi
}

download_archive() {
    local temp_archive
    mkdir -p -- "$DOWNLOAD_DIR"
    temp_archive="$(mktemp "${DOWNLOAD_DIR}/.llvm-mos-v${SDK_VERSION}.XXXXXX")"
    trap 'rm -f -- "${temp_archive:-}"' RETURN

    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "$temp_archive" "$SDK_URL"
    elif command -v wget >/dev/null 2>&1; then
        wget --output-document="$temp_archive" "$SDK_URL"
    else
        error 'curl or wget is required to fetch the LLVM-MOS SDK.'
        return 1
    fi

    if ! archive_is_valid "$temp_archive"; then
        error "downloaded archive failed SHA-256 or xz validation: ${SDK_URL}"
        return 1
    fi
    mv -f -- "$temp_archive" "$ARCHIVE"
    trap - RETURN
}

install_sdk() {
    local install_parent stage_dir compiler_path payload_root

    if [[ -x "${SDK_ROOT}/bin/${SDK_COMPILER_NAME}" ]]; then
        return 0
    fi
    if [[ -e "$SDK_ROOT" ]]; then
        error "install directory already exists but has no ${SDK_COMPILER_NAME}: ${SDK_ROOT}"
        error 'Move that incomplete directory aside or set PCE_LLVM_MOS_SDK_ROOT to another local path.'
        return 1
    fi

    if ! archive_is_valid "$ARCHIVE"; then
        rm -f -- "$ARCHIVE"
        error "downloading LLVM-MOS SDK ${SDK_VERSION} to ${ARCHIVE}"
        download_archive
    fi
    if ! archive_is_valid "$ARCHIVE"; then
        rm -f -- "$ARCHIVE"
        error 'cached or downloaded archive does not match the pinned SHA-256 digest.'
        return 1
    fi

    # Reject absolute paths and parent traversal before extracting the archive.
    if ! tar -tJf "$ARCHIVE" | awk 'BEGIN { bad = 0 } /^\// { bad = 1 } /(^|\/)\.\.(\/|$)/ { bad = 1 } END { exit bad }'; then
        error "archive contains an unsafe path: ${ARCHIVE}"
        return 1
    fi

    install_parent="$(dirname -- "$SDK_ROOT")"
    mkdir -p -- "$install_parent"
    stage_dir="$(mktemp -d "${install_parent}/.llvm-mos-${SDK_VERSION}.XXXXXX")"
    trap 'rm -rf -- "${stage_dir:-}"' RETURN
    if ! tar -xJf "$ARCHIVE" --no-same-owner --no-same-permissions -C "$stage_dir"; then
        error "could not extract ${ARCHIVE}"
        return 1
    fi

    compiler_path="$(find -L "$stage_dir" -type f -path "*/bin/${SDK_COMPILER_NAME}" -print -quit)"
    if [[ -z "$compiler_path" ]]; then
        error "archive does not contain bin/${SDK_COMPILER_NAME}"
        return 1
    fi
    payload_root="${compiler_path%/bin/${SDK_COMPILER_NAME}}"
    if [[ "$payload_root" == "$compiler_path" || ! -d "$payload_root" ]]; then
        error "could not identify the SDK root in ${ARCHIVE}"
        return 1
    fi

    # Keep the local install at a stable, user-writable path; never touch /usr.
    if ! mv -T -- "$payload_root" "$SDK_ROOT"; then
        if [[ ! -x "${SDK_ROOT}/bin/${SDK_COMPILER_NAME}" ]]; then
            error "could not publish the local SDK installation at ${SDK_ROOT}"
            return 1
        fi
        # A concurrent Make invocation installed the same SDK first.
    fi
    trap - RETURN
    rmdir --ignore-fail-on-non-empty "$stage_dir" 2>/dev/null || true
}

ensure_bin() {
    local found_bin
    if found_bin="$(path_compiler_bin)"; then
        printf '%s\n' "$found_bin"
        return 0
    fi

    require_supported_host

    if [[ -x "${SDK_ROOT}/bin/${SDK_COMPILER_NAME}" ]]; then
        printf '%s\n' "${SDK_ROOT}/bin"
        return 0
    fi

    install_sdk
    if [[ -x "${SDK_ROOT}/bin/${SDK_COMPILER_NAME}" ]]; then
        printf '%s\n' "${SDK_ROOT}/bin"
        return 0
    fi
    error "installed SDK does not provide ${SDK_COMPILER_NAME}"
    return 1
}

case "${1:-}" in
    --ensure-bin)
        ensure_bin
        ;;
    --print-env)
        bin_dir="$(ensure_bin)"
        printf 'export LLVM_MOS_BIN_DIR=%q\n' "$bin_dir"
        printf 'export PATH=%q:"$PATH"\n' "$bin_dir"
        ;;
    *)
        printf 'Usage: %s --ensure-bin | --print-env\n' "$0" >&2
        exit 2
        ;;
esac
