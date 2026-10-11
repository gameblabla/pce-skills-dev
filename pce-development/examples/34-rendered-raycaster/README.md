# 34 — 128×128 paired-BAT raycaster

**Example implementation. Not speed optimized, has issues.**

This is a demonstration of a 128×128, 16-colour *logical* raycaster on the PC Engine. Its physical display is 512×224, but the paired-BAT trick does not deliver 512 independently drawn horizontal pixels. Two 4-bit colour indices are encoded in each BAT word. The 256 static tile patterns live in VRAM, and the sky/floor backdrop is initialized once. Each frame updates **changed wall spans** within the BAT, not a whole software framebuffer.

The previous 128×64 atomic example was removed, including its build target, page-swap code and tests. The only maintained raycaster presentation is progressive 128×128. Reference shaders remain solely for same-resolution comparisons.

## Presentation path

The raycaster uses 128 ray directions, center-first paired-column ordering, a fixed 16-colour palette, close-range 32×32 wall texels, and lookup-driven wall shading. A sparse raster IRQ remaps 128 logical rows to 224 scanlines. The second half of the 128×64 **hardware BAT** is circularly shifted by one row to prevent a floor-coloured scanline at the midpoint boundary; this is not an alternate 128×64 image mode.

The staged uploader composes wall BAT words before VBlank and transfers a maximum of **96 words per frame**, in interrupt-bounded bursts of at most eight words. For each physical vertical run, the VDC's auto-increment-by-128 remains active between bursts; the code only reselects the data port after raster IRQs and reprograms the address at a new segment or across the shifted BAT-page wrap. This avoids repeated MAWR register writes for consecutive bursts. A compile-time comparison build can use `-DRAY_PRESENT_CONTIGUOUS=0` to restore per-burst address setup.

**Important:** More than 96 words per frame has produced raster or incomplete-bitmap regressions in emulator tests, even when a shorter test appeared to pass. This is not a hardware-proven throughput limit. Do not increase the budget, widen burst length, or change the raster IRQ without validating both the 540-frame consecutive-turn sweep *and* the 1,080-frame movement stress. The current renderer is progressive and can visibly tear or respond slowly. A dirty-view commit is not a full-screen FPS measurement.

## Build and verify

With the LLVM-MOS PCE toolchain on `PATH`:

```sh
make                        # 128×128 ROM: build/34-rendered-raycaster.pce
make tables-check
PCE_HEADLESS=/path/to/pce-headless make column-regression
PCE_HEADLESS=/path/to/pce-headless make interaction-test
```

`make vram-present-compare` builds both address-setup implementations, checks their exact stationary screenshot pixels, and compares dirty-view counts from the same emulated input sequence. `make column-benchmark` reports VRAM words, loop updates and completed dirty-view passes. `make raster-sweep` captures consecutive turning screenshots and checks for blank frames and the midpoint seam. `make bitmap-stress` tests sustained movement. The optional grid-traversal experiment remains opt-in (`-DRAY_GRID_CROSSING=1`), because earlier measurements showed a CPU-cycle reduction without convincing whole-image throughput improvement.

## Verified VRAM presentation comparison (emulator only)

`make vram-present-compare` runs the old per-burst address setup against the
contiguous-address implementation under identical controller scripts, followed
by an independent screenshot equivalence test. In the 1,080-video-frame
benchmark, **both** produce 14 changed-view passes, **1.500** turning
passes/second, and write **60,281 BAT words**. Their stationary screenshots
match over **135,520 RGB pixels**. The optimized path omits redundant VDC
MAWR register writes, but **has not demonstrated a whole-screen FPS increase**.
The 96-word contiguous build passed 540 consecutive rotation screenshots,
1,080 movement frames (19 completed dirty-view passes), and the native
profiler budget. A 104-word variant still failed sustained-movement tests;
this failed variant is not a release build.

## Limitations and references

This is educational source, not a production engine. FPS remains constrained by live BAT uploads and IRQ timing; the floor remains screen-anchored, 128×128 logical pixels look blocky, and emulator success is not physical-hardware certification.

The bitmap technique is based on [PCEdev's description](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/). The VCS-inspired coverage-span compositor and optional grid traversal are documented in `docs/vcs-port.md`, with the MIT-licensed reference sources retained. Older experimental variants remain in Git history for comparison, but are no longer build targets.
