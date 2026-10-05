# Project cookbook index

The worked examples live inside this skill bundle so they remain available in
a fresh workspace without a game checkout or exported conversation history.
They are LLVM-MOS PCE CD recipes; any code-shaped block marked pseudocode must
be bound to actual LLVM-MOS SDK headers, linker sections, and BIOS interfaces
before compilation.

Start with [`examples/00-project-template/README.md`](../examples/00-project-template/README.md)
for the project layout and test ladder. Then use the matching recipe:

- Cold boot and visible text:
  [`01-cdrom2-hello/README.md`](../examples/01-cdrom2-hello/README.md)
- Static image, palettes, patterns, BAT:
  [`02-static-screen/README.md`](../examples/02-static-screen/README.md)
- CD sector loading and named files:
  [`03-cd-to-aram-files/README.md`](../examples/03-cd-to-aram-files/README.md)
- Arcade RAM to VRAM and TII/TDD/TIN/TIA/TAI:
  [`04-aram-to-vram/README.md`](../examples/04-aram-to-vram/README.md)
- CD-DA, ADPCM, DDA, and PSG:
  [`05-sound-samples/README.md`](../examples/05-sound-samples/README.md)
- Sprite patterns, SAT, and admission:
  [`06-sprites-and-sat/README.md`](../examples/06-sprites-and-sat/README.md)
- Large staged animations:
  [`07-large-animation/README.md`](../examples/07-large-animation/README.md)
- Platformer, racing, and shmup structures:
  [`08-platformer/README.md`](../examples/08-platformer/README.md),
  [`09-racing/README.md`](../examples/09-racing/README.md), and
  [`10-shmup/README.md`](../examples/10-shmup/README.md)
- Image-guided HUD adjustment:
  [`11-visual-request/README.md`](../examples/11-visual-request/README.md)
- Code relocation and Python arithmetic:
  [`12-bank-relocation/README.md`](../examples/12-bank-relocation/README.md) and
  [`14-python-math/README.md`](../examples/14-python-math/README.md)
- Emulator/MCP debugging:
  [`13-headless-debugging/README.md`](../examples/13-headless-debugging/README.md)

This folder does not include any commercial game source or claim a recipe is
compiled against a particular local SDK version. When a base-code checkout is
provided by the user, inspect it and map each recipe operation to the existing
implementation rather than inventing a parallel API. If no source or SDK is
available, keep the output at architecture/pseudocode level and identify what
is needed to make it buildable.
