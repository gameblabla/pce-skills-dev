# LLVM-MOS SDK setup for scratch projects

The compiler driver for this skill's target is `mos-pce-clang`. HuC6280 names
the console CPU; it is not a compiler or assembler choice. Use the active
project's pinned LLVM-MOS when one is configured.

## Makefile bootstrap

For each new project created from an example, copy these starter files into
the project's `tools/` directory and use the starter Makefile:

- [`examples/starter/Makefile`](../examples/starter/Makefile)
- [`examples/starter/tools/llvm-mos-sdk.mk`](../examples/starter/tools/llvm-mos-sdk.mk)
- [`examples/starter/tools/llvm-mos-sdk.sh`](../examples/starter/tools/llvm-mos-sdk.sh)
- [`examples/starter/tools/check-pce-bios.sh`](../examples/starter/tools/check-pce-bios.sh)

The Makefile include looks for `mos-pce-clang` on `PATH`. If it is present, its
resolved `bin` directory is prepended to the environment used by Make recipes
and recursive Make calls. If absent, the helper downloads LLVM-MOS SDK 23.2.0,
checks the pinned SHA-256 digest, extracts it under the user's local data
directory, and exports that SDK's `bin` directory to Make. Automatic download
is for Linux x86_64, matching the requested release archive. On another host,
install its matching SDK and put `mos-pce-clang` on `PATH`. The helper does not
write to system directories.

Defaults:

- Archive: `${XDG_CACHE_HOME:-$HOME/.cache}/pce-development/downloads/llvm-mos-linux-v23.2.0.tar.xz`
- Installation: `${XDG_DATA_HOME:-$HOME/.local/share}/pce-development/toolchains/llvm-mos-sdk/23.2.0`

Override those paths with `PCE_LLVM_MOS_DOWNLOAD_DIR` and
`PCE_LLVM_MOS_SDK_ROOT`. The bootstrap needs `curl` or `wget`, `xz`, `tar`, and
`sha256sum` or `shasum` only when it must download or verify the archive. Use
`make clean` without triggering installation. Every project compile, assemble,
and link target must depend on `toolchain` so a missing compiler fails before
the build command runs.

To export the selected compiler path in an interactive shell instead of running
Make, run this from the project directory:

```sh
eval "$(tools/llvm-mos-sdk.sh --print-env)"
```

Make exports `$PATH` only to its own recipes and child processes; this command
exports it to the current interactive shell.

## Missing CD System Card BIOS

The compiler SDK does not contain System Card firmware. Before a headless CD
boot, run `make bios-check`. If no file is configured, it creates and prints
this user-local folder in the terminal:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/pce-development/bios
```

Place the user's extracted System Card `.pce` image there, then set
`PCE_SYSTEM_CARD_BIOS` to that file's full path. Use `PCE_BIOS_DIR` to change
the suggested folder. The check does not copy, download, or package firmware.
