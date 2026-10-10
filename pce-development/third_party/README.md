# Third-party source

This folder contains the supplied PCE headless source snapshot, its build
scripts, headless frontend notes, MCP wrapper, upstream documentation, and
component license notices. Preserve all source licenses and notices.
The profiler enhancements (physical-PC master-tick sampling, frame-boundary
clock accounting, and headless `prof_start`/`prof_dump` RPC validation) are
tracked in this repository. `make headless-build` rebuilds the frontend and
`make cycles-check` exercises native and report-side profiler logic. Mednafen keeps two complete source copies: the buildable `mednafen/src/` tree
and the `mednafen/include/mednafen/` mirror. Keep both copies byte-identical
when changing vendored source; `test_vendor_mirror.py` checks the whole tracked
mirror during `make test`, including profiling, tracing, palette and VDC hooks.

An independently recovered emulator source snapshot contains 1,553 files and
matches Git commit `c6a0670` *exactly*; its patches cover changes since the
first import (`c8e4dd3`). It predates profiler commit `7152f95` and is not a
replacement for the current source. Historical emulator fixes already have
tracked commits; they do not need the old patch reapplied.

Locally generated object files, libraries, configured build files, and
executables are not part of the skill bundle.

Start with the headless frontend notes in the source snapshot. The public skill
does not include a compiled binary, game ROM/disc image, or BIOS. Project Make
targets select the configured executable; keep source and executable details
inside the project helpers rather than coding-agent prompts.
