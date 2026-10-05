# Common PC Engine failure patterns

These patterns are included here so the skill works in a fresh conversation
without access to earlier chat logs, issue trackers, or commit history. They
are diagnostic leads, not automatic explanations. Reproduce the symptom and
confirm each relevant mechanism in the active source and hardware setup.

## A stable table can still produce a shifting scanline

If generated per-line scroll values are unchanged but an occasional row moves,
inspect interrupt latency and VDC register timing. A long non-interruptible
block transfer, broad IRQ-masked copy, or audio setup can miss the HBlank
window even when the table is correct.

- Capture the relevant values across the failing frame.
- Instrument interrupt assertion, handler entry, interrupted work, and the
  VDC write relative to the line latch.
- Repeat with audio, sprite upload, and other transfer paths active.
- Reduce only the measured blocking section and retest both static and moving
  scenes under simultaneous effects.

Do not assume one transfer burst size is safe for every scene. Measure the
active mode and worst-case load. Use Python to calculate the cycle budget.

## One-frame sprite/background mismatch

The VBlank edge is a publication boundary. If the background scroll advances
while the matching SAT page is not ready, actors appear to jump relative to
the world. If VDC address selection is interrupted between register writes,
subsequent bytes may land in a different register.

Check which generation of SAT, scroll, BAT, palette, raster table, and cache
ownership is active on each displayed frame. Publish coherent state together.
Keep only the register setup atomic; do not mask interrupts for a frame-sized
copy.

## Hardware admission can affect game rules

SAT capacity and the per-scanline sprite width limit are gameplay constraints.
Draw order determines which items remain visible. Optional particles and
projectiles can be refused under pressure; a refused projectile must not still
cause invisible damage. Preserve essential player and hazard sprites first,
then throttle optional effects or future spawns based on measured refusal.

Test the empty case, a normal case, and the crowded worst case. Confirm the
test reaches the intended scene before trusting an empty overflow report.

## Cache capacity includes content still displayed

When a scrolling map enters a new column, the outgoing column may remain
visible until the next VBlank. A tile slot that looks unused to the CPU can
still be referenced by the displayed BAT. Hold or pin its slot until the
scroll change is published; keep asset-side slack for measured peak
uniqueness.

Check cache references, BAT writes, tile upload timing, and the frame when
scroll takes effect. A static screenshot can miss this transition race.

## Generated assets and tests can drift separately

An exporter can bind the wrong source sheet while the renderer is correct.
Bind per-character inputs explicitly and preview every generated character.
Tests should identify assets by semantic names/manifests rather than numeric
IDs that shift when strips are inserted.

Before refreshing a visual fixture, confirm the new output is intended. A test
may also pass without exercising its target scene; validate preconditions and
keep a meaningful assertion after updating the fixture.

## A full bank report does not identify a safe destination

Linker-reported free bytes do not include every temporal runtime role. A bank
may be borrowed by a CD loader or audio path, or be needed by a nested overlay.
Trace callers, the active MPR mapping, data lifetime, IRQ/stack reachability,
and transfer lifetime before moving code. Inspect post-link sections after LTO.

See `banks-and-overlays.md` for the full relocation procedure and Python
capacity ranker. Historical numbers are never current build evidence.

## Claim only what the test observed

A deterministic seeded emulator scenario can prove the state path it executes;
it does not automatically prove a complete playthrough, every-stage frame
rate, CD hardware behavior, or physical console timing. Record build identity,
BIOS/emulator configuration, input/state setup, capture, and exact assertions.
Keep emulator evidence, human playthrough, and physical hardware results
separate.
