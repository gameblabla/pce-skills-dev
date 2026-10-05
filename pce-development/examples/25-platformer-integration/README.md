# Example 25: integrate platformer collision, scrolling, and HUD

This is an integration case study and review checklist, not a standalone ROM.
Examples 08, 17, 18, and 21 each demonstrate a smaller path. They do not become
a complete platformer by copying their source files into one project.

## Lock the target before implementation

Write down whether the requested deliverable is a HuCard preview or a bootable
CD-ROM² disc. The numbered examples mostly build `.pce` HuCard ROMs with
`mos-pce-clang`. A Makefile comment calling that output “Super CD-ROM²” does
not change the target. A CD deliverable needs the project's CD compiler,
IPL/disc layout, disc-image builder, and a compatible user-supplied System Card
for emulator boot. Example 03 shows the bundle's CD build switch and the
remaining project-specific packaging work. Report each artifact by its real
type; do not claim CD boot was tested after loading the HuCard preview.

Use `examples/03-cd-to-aram-files/Makefile` as the CD/HuCard compiler-switch
starting point, not the generic HuCard-only starter. Its `PCE_CDROM2=1` output
is still an application binary; the game project must provide the disc image
rule before a CD `run` target can boot it.

Do not embed the HuCard preview's full `demo_assets.h` arrays into a CD
application by default. The CD linker places application data under a
different, constrained runtime layout. Inspect its map and memory report; put
large art and map payloads in the project's disc manifest and load them through
the CD/Arcade-RAM path described by Example 03. Keep a small intentional
boot/test screen in resident data if the project needs one.

## Define shared gameplay geometry

Before drawing or moving anything, record these project facts in named types:

- World origin and units; camera origin and legal range.
- Player collision width/height and whether `(x, y)` names its top-left,
  feet-center, or another anchor.
- Sprite art's visible bounds relative to its hardware SAT anchor.
- Platform collision bounds and the exact art drawn for those bounds.
- Screen-space coordinates and reserved HUD/effect/world SAT entries.

Keep physics in world coordinates. Resolve horizontal and vertical axes
separately. When descending through a platform top, place the actor's feet on
that top and zero vertical velocity. Draw the player from the same position
and anchor used by collision. Keep the hardware's SAT coordinate bias in one
adapter; confirm it from the active helper and SDK before changing it.

Build both collision and art from the same platform/map record. Do not use a
coarse `is_solid(x, y)` area that does not match what the renderer draws. Keep
the previous position when resolving crossings so a fast fall cannot skip a
thin platform. Use the Python helper for unit conversions and budget totals.

## Compile before adding the next subsystem

Build after each source file or subsystem, with the requested target and the
project's normal warning policy. Before declaring a build valid, check that:

- Input names and bit masks come from the active SDK header; do not redefine
  names such as `KEY_LEFT` or guess sprite attribute constants.
- Every called function has a matching declaration before use.
- Generated arrays have the declared dimensions and the initializer count
  matches those dimensions. Keep generated art in a reproducible asset step
  when hand-written data becomes hard to audit.
- Physics uses an explicit integer or fixed-point format. A fractional
  constant assigned to an integer velocity can truncate to zero; use a named
  scale and test movement over several frames.

After every source change, rerun the complete target build. A stale `.pce` or
`.bin` left from an earlier successful build is not evidence that current
sources compile. Report the exact command and exit status.

If the CD linker reports a RAM overflow, inspect the map/report and identify
which arrays or generated assets occupy the overflowing region. Move long map
and art data to the project's disc/Arcade-RAM loading path or use a compact
representation. Never silence the error by shrinking the requested level,
removing required enemies, or moving the goal closer without saying the target
was changed. A one-minute timer is not proof that the route takes one minute:
define the movement speed, route length, frame rate, and timer behavior, then
use `scripts/calc.py` for the route-time calculation.

## Publish a matching camera frame

The camera changes presentation, never player world position. For each frame:

```text
read_and_normalize_input()
integrate_player_in_world_coordinates()
resolve_horizontal_then_vertical_collision()
update_enemies_and_game_state()
camera_x = clamp(camera_from_player_world_x())
stream_entering_world_map_columns_into_the_bat_ring(camera_x)
build_world_sat_entries(world_position_minus_camera_position)
build_hud_entries_in_screen_coordinates()
publish_matching_bat_scroll_and_sat_at_the_same_vblank()
```

Pseudocode only. Use the actual SDK and project's frame-publication adapter.
The 64-by-32 demo BAT and its sample artwork are a small repeating screen
fixture, not a streamed multi-screen level. Scrolling that fixture across a
long level repeats its art and any tutorial labels embedded in the BAT. Inspect
the generated BAT/source image, then either replace it with a real streamed
map or keep the camera inside the fixture's documented extent.

Give every sprite a distinct SAT slot. In `examples/08-platformer/src/demo_video.c`,
`demo_draw_sprite()` is a convenience wrapper for slot zero; repeated calls in
a loop overwrite one another. Use explicit slots or render terrain into the
background map. Reserve and document slots for world actors, pole/effects, and
HUD, clear stale slots, and check per-scanline admission before publishing.

The PC Engine's one scrolling background plane cannot keep ordinary BAT text
fixed while the playfield scrolls. Use reserved screen-space sprite entries for
the HUD, or build a tested raster split/update path. Draw actual glyphs and
timer digits, keep their screen coordinates independent of the camera, and
establish their priority over playfield actors. Do not print controls into a
static demo BAT and leave them there for a scrolling scene.

When the protagonist looks duplicated, inspect the background BAT for baked-in
copies, all SAT entries submitted for that logical actor, and every tile in a
metasprite. Verify that the emulator loaded the current image before changing
assets. For an unexpected palette, trace the sprite pattern's pen indices, the
copied VCE palette, and the palette number encoded in its SAT attribute. For a
floating/sunken actor, compare its visible feet and collision-box bottom with
the rendered platform top and collision top in one captured frame; account for
the SDK/hardware SAT origin exactly once.

## Reach the states you claim to test

Add P2TR v1 instrumentation using
[`platformer rules`](../../references/platformer-rules.md). Read the record's
address from the current symbol table, then run `make trace` with short input
scenarios. This produces a text report a non-multimodal agent can use to
identify movement, gravity, landing, support, art/collision, and camera errors.
A neutral boot alone proves none of those gameplay paths.

Copy [`platformer-scenario.example.json`](platformer-scenario.example.json)
into the project and adapt its button durations to known map coordinates.
After adding the `pce_platformer_trace` state and building the debug image, the
Make helper resolves the symbol from the current ELF:

```sh
make trace
```

If the project emits no symbol-bearing ELF, pass
`PCE_PLATFORM_TRACE_ADDRESS` from the current link map. The Make target writes a
compact JSON report to `build/platformer-trace.json`; inspect frame-addressed
findings before editing physics or camera code.

Capture and inspect at least these matched image/state pairs:

| State | Check |
|---|---|
| Title | Text/art are intentional and no gameplay tutorial labels leak through. |
| Initial play | Player's visible feet align with the ground collision top. |
| Elevated landing | Player remains supported at rest; the drawn platform spans the collision area. |
| Mid-level scroll | Terrain and actors move together; no static BAT label or pattern wraps into view. |
| HUD during scroll | Timer changes with game time and stays in the same screen position with deliberate priority. |
| Enemy contact | A downward stomp kills/bounces; a side hit enters the death path. |
| Goal | The flag animation is visible before the end transition. |

Also inspect generated pattern/BAT data and SAT entries when a screenshot
disagrees with collision state. The examples' neutral-input screenshots cannot
substitute for these states.

## Verify the emulator and artifact

From a nested scratch project, use `make run` or `make debug` for a neutral
capture. Use `make trace` with P2TR v1 for deterministic gameplay. Copy these
targets and their helpers from `examples/starter` if the project does not have
them. They select the configured headless emulator and isolate run state; a
local agent should not discover or launch an emulator executable on its own.

At completion, report the compiler, build command, exact output artifact and
size/type, scenario frames/buttons or seeded state, trace/screenshot paths, and
which table rows were actually reached. For CD, include the disc image and
System Card version; if either is unavailable, report a HuCard preview or
incomplete CD build accurately. Clearly separate game-authored trace evidence,
screenshot inspection, emulator execution coverage, and physical-console tests.
