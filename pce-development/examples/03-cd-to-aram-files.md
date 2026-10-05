# Example 03: CD sectors to Arcade RAM and named files

**Build contract:** A project created or changed from this recipe copies the [starter Makefile](starter/Makefile) and all files under [`starter/tools/`](starter/tools/), includes `tools/llvm-mos-sdk.mk`, and makes each compile, assemble, and link target depend on `toolchain`. CD boot targets also run `bios-check`.

CD-ROM reads generally pass through a CPU-visible destination or hardware DMA
window before software copies the bytes to Arcade RAM. Use the LLVM-MOS PCE CD
SDK's BIOS headers and linker symbols for the exact CD API/MPR window. Keep
that adapter contract explicit; do not invent SDK function names.

## Disc build data

Generate a manifest for every file containing a stable semantic name, sector
start, sector count, true byte length, target Arcade RAM address, and checksum.
Validate that named extents do not overlap protected disc areas and that the
last file byte is inside its extent. Use Python for all extent and range math.
At boot, read the manifest or use linker-generated extent symbols from the
image builder; never duplicate sector numbers in unrelated C files.

## Load flow

```text
load_file(name):
    entry = find_manifest_entry(name)
    validate_entry(entry)
    stop_or_pause_audio_if_disc_policy_requires_it()
    remaining = entry.sector_count
    source_sector = entry.first_sector
    destination = entry.arcade_address
    while remaining != 0:
        chunk = choose_chunk_that_fits_cpu_window_and_card_api()
        read_cd_into_cpu_visible_window(source_sector, chunk)
        copy_window_to_arcade_port(destination, chunk.true_bytes)
        source_sector += chunk.sectors
        destination += chunk.true_bytes
        remaining -= chunk.sectors
    verify_checksum_if_available(name)
```

This is pseudocode. `choose_chunk...` must use the LLVM-MOS PCE CD SDK's actual maximum and
sector granularity. If a CPU code bank doubles as a transfer window, document
when the loader overwrites it, which MPR changes, how code is restored, and
which loader/IRQ/stack code stays reachable.

## Failure handling and tests

- Reject unknown filenames, zero/oversized extents, and destination overflow.
- Return a visible error on CD timeout/status failure; don't continue with
  partially loaded data.
- Test a small file, a multi-window file, a bank/window crossing, a final
  partial sector, and a deliberately corrupted manifest/checksum.
- Compare loaded bytes to the builder's source checksum in a host or emulator
  test. A successful BIOS call alone does not prove the copied destination is
  correct.
- Verify loading while CD-DA, ADPCM, or timer-driven playback is active only
  if that concurrency is supported and tested by the chosen SDK.
