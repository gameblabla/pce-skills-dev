#!/bin/sh
set -eu

mode=${1:?usage: run-pce-headless.sh run|debug image}
image=${2:?usage: run-pce-headless.sh run|debug image}
case "$mode" in
  run|debug) ;;
  *) echo "mode must be run or debug" >&2; exit 2 ;;
esac

project_dir=$(pwd)
absolute_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$project_dir" "$1" ;;
  esac
}

image=$(absolute_path "$image")
frames=${PCE_RUN_FRAMES:-120}
screenshot=$(absolute_path "${PCE_RUN_SCREENSHOT:-build/headless.png}")
base_dir=$(absolute_path "${PCE_HEADLESS_BASE_DIR:-build/headless-base}")
mkdir -p "$(dirname "$screenshot")" "$base_dir"

emulator=${PCE_HEADLESS:-}
if [ -z "$emulator" ]; then
  search_dir=$project_dir
  while :; do
    for candidate in "$search_dir"/PCE/*headless*; do
      if [ -x "$candidate" ] && [ -f "$candidate" ]; then emulator=$candidate; break; fi
    done
    [ -n "$emulator" ] && break
    [ "$search_dir" = / ] && break
    search_dir=$(dirname "$search_dir")
  done
fi

if [ -z "$emulator" ]; then
  for candidate in "$(dirname "$0")"/../../../third_party/*/pce-headless; do
    if [ -x "$candidate" ] && [ -f "$candidate" ]; then emulator=$candidate; break; fi
  done
fi

if [ -z "$emulator" ] || [ ! -x "$emulator" ]; then
  cat >&2 <<'EOF'
No configured PCE headless emulator was found.
Set PCE_HEADLESS or follow the pce-development headless-emulator guide.
EOF
  exit 2
fi

set -- "$emulator" --rom "$image" --frames "$frames" \
  --screenshot "$screenshot" --base-dir "$base_dir"
if [ -n "${PCE_SYSTEM_CARD_BIOS:-}" ]; then
  set -- "$@" --bios "$(absolute_path "$PCE_SYSTEM_CARD_BIOS")"
fi
if [ "$mode" = debug ]; then
  coverage=$(absolute_path "${PCE_COVERAGE:-build/coverage.json}")
  mkdir -p "$(dirname "$coverage")"
  set -- "$@" --cov "$coverage"
  if [ -n "${PCE_DEBUG_DISASM:-}" ]; then
    set -- "$@" --disasm "$PCE_DEBUG_DISASM"
  fi
fi

printf 'Configured headless PCE run.\nImage: %s\nScreenshot: %s\n' \
  "$image" "$screenshot"
if [ "$mode" = debug ]; then printf 'Coverage: %s\n' "$coverage"; fi
exec "$@"
