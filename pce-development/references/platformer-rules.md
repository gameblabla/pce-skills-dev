# Platformer rules and text-only diagnostics

Use this guide with the [platformer integration example](../examples/25-platformer-integration/README.md).
These rules describe state that can be checked from source, maps, and a
per-frame trace even when the reviewing agent cannot inspect images.

## Gameplay invariants

1. **Choose one world-space collision box.** State whether player `x,y` is its
   top-left and define its width and height. Use signed fixed-point values for
   position and velocity. Keep camera coordinates out of physics.
2. **Apply gravity on every airborne update.** Integrate vertical velocity,
   then position, in the same fixed-point units. `vy > 0` means downward.
   A fractional gravity value must survive integer conversion; check its
   accumulated result over many frames.
3. **Land by crossing a surface top.** Keep the previous and proposed feet
   positions. A landing needs downward motion, horizontal overlap, and a
   previous-feet/current-feet crossing of the platform's collision top. Snap
   the feet to that top, set grounded, clear downward velocity, and emit one
   landing event. A one-way platform ignores upward crossings.
4. **Derive grounded from collision resolution.** Do not set it at spawn or
   preserve it after walking off an edge. A grounded trace must show a
   collidable surface under the feet at the same world coordinates.
5. **Separate input edges from held input.** Walking follows held directions;
   jumping normally follows a newly pressed button while grounded. Test the
   SDK's actual controller names and values. Do not define replacement macros
   for SDK keys.
6. **Transform presentation once.** Draw world actors at world position minus
   camera position. Keep the visible artwork offset from the collision box
   explicit. Apply the SDK/hardware SAT origin adjustment in one rendering
   adapter only. Keep a scrolling HUD in screen coordinates with a documented
   display-priority path.
7. **Use one map record for art and collision.** Report each test surface's
   drawn rectangle and collision rectangle from the same map data. This makes
   a pass-through, invisible wall, or floating visual platform distinguishable
   from a rendering-only offset.

## Publish a P2TR v1 state record

Copy [`tools/pce/platformer_trace.h`](../tools/pce/platformer_trace.h) into the
game and define two consecutive `volatile PcePlatformerTrace` entries named
`pce_platformer_trace` in main RAM. Alternate between them after each gameplay
frame's physics/collision and actor submission have been prepared. Build them
into the debug image only if RAM or
timing budgets require a release-only exclusion. `make trace` reads the symbol
address from the adjacent ELF with the LLVM-MOS symbol tool; pass
`PCE_PLATFORM_TRACE_ADDRESS` from the map only if the project emits no ELF.
Never guess an address or assume both records fit in free RAM.

The record is 216 bytes. It contains a signature/version, scene/frame/input,
camera position, player collision box and velocity, visible sprite bounds,
actual submitted screen coordinates, SAT range/palette, and up to four nearby
platforms with separate collision and drawn rectangles. Coordinates and sizes
use signed Q16.8 pixel units (divide raw integers by 256). The PCE button mask
uses active-high bits: I, II, Select, Run, Up, Right, Down, Left, III, IV, V,
VI in bits 0 through 11. Publish the fields from the values the game really
uses; do not fill the trace with expected or reconstructed values.

Keep both records wholly inside the project's mapped main RAM. Verify their full
432-byte address range in the current map and confirm they do not overlap another
global. Use each record's low `reserved` byte as a publication sequence: mark it
odd before writing and write its next even value only after every field is
complete. Leave the active record untouched while building its replacement,
then swap the active index. The headless reader chooses the newest even sequence,
so each scenario step represents one complete game update. The report includes both the game-authored
frame and the headless emulator frame. If the game frame still repeats or jumps
between adjacent samples, inspect the VBlank update and frame publisher before
diagnosing movement or collision. Treat a counter discontinuity as a timing
lead, not proof of a physics bug.

## Drive repeatable scenarios and read the report

When the MCP server exposes `run_platformer_scenario`, use it instead of a
neutral run for gameplay. The tool holds each requested PCE button set for the
specified frame count and reads the P2TR record after every frame. For a
project Make target, use the copied `tools/platformer-scenario.example.json`
and run `make trace`; the helper resolves `pce_platformer_trace` from the
current ELF automatically. Example MCP input:

```json
{
  "trace_address": "0x2200",
  "steps": [
    {"frames": 1, "buttons": []},
    {"frames": 30, "buttons": ["right"]},
    {"frames": 1, "buttons": ["i"]},
    {"frames": 20, "buttons": []}
  ]
}
```

Replace the sample address with the current map address. Start from a known
title/game state and use a fresh reset or state for each comparison. Button
lists are held levels: a tap is one frame followed by a release segment.

Run short scenarios that isolate one rule before attempting a full level:

- **Spawn/support:** first gameplay frame, feet and ground top, grounded flag.
- **Gravity:** stand still after stepping off a ledge; compare `y`, `vy`, and
  per-frame changes until the fall or landing completes.
- **Walking:** hold each direction on open ground; compare input, world `x`,
  velocity, collision flags, and camera `x`.
- **Jump/landing:** issue a one-frame jump press, release it, then trace the
  descent across a known platform. Check the landing event, support, snapped
  feet, and reset `vy`.
- **Scrolling:** move through a map seam; verify world position remains
  continuous, camera changes once, and submitted screen position matches the
  world/camera relationship.
- **Enemy/goal:** stage a downward stomp and a side contact separately, then
  trace death/respawn and goal events.

For each input segment, compare the requested buttons with the `buttons` mask
observed in the P2TR samples. A transition can land on either side of the game's
controller poll; use the observed mask and `input_latch_delay_samples` when
aligning a jump or movement change to a frame. Do not diagnose an input bug from
the JSON segment boundary alone.

The report lists jump/landing/death/goal event frames and calls out missed
platform crossings, grounded-without-support, landing state/velocity mismatches,
art/collision top mismatch, stalled gravity or movement, and sprite/camera
coordinate mismatch. Treat these as leads tied to exact frames. Inspect the
source update order, map data, and linker map before changing code. A trace is
game-authored: it cannot independently prove that pixels were drawn, the VCE
palette looked correct, or the console ran at physical timing. Use the
headless screenshot or video for rendering evidence; a text-only model should
state which claims the trace proves and which still need image/hardware review.

If this MCP tool is unavailable, add an equivalent deterministic debug input
hook and emit the same ABI as CSV/JSON from the game test build. Do not claim a
gameplay path was tested when no input was applied.
