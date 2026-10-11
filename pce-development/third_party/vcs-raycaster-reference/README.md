# Atari VCS raycaster reference

These three **unaltered** assembly files came from the user-supplied
`vcs-demo-raycaster-master.zip`, authored by Guillaume Laudet (Kezax /
Dentifrice), 2018. The source is provided under the bundled MIT license.

The runtime used by the PCE project does **not** assemble or link VCS TIA
instructions. The PCE implementation in
`examples/34-rendered-raycaster/src/main.c` independently adapts the VCS
height-threshold output conversion from `raycast_converter.asm` into a
paired-BAT wall-span compositor.

Reference details:

- `raycast.asm`: tile-intercept traversal with tangent tables / fixed-point arithmetic
- `raycast_converter.asm`: packed wall heights, height thresholds and XOR playfield deltas
- `mul8.8x8.asm`: 8.8-by-8 fractional multiplication routine for the VCS

Different hardware: TIA playfield-register writes, mirrored half-screen and
bank-switching routines must **not** be transplanted into HuC6280/VDC code.
