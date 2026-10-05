# Example 15: 320-dot and 512-dot display modes

**Build contract:** Copy the shared starter Makefile and its tools, use the pinned LLVM-MOS PCE CD SDK, and run the new mode through an emulator configured for CD hardware. The exact Saber Rider register values below describe that revision; they are not a promise that every display or TV shows identical overscan.

The Saber Rider port uses two wide modes. The title, options, and character select use a 320 by 224 display at the VCE 7 MHz pixel-clock setting. Race rendering switches to 512-dot mode at the VCE 10 MHz setting. The game first initializes the VDC in its ordinary 256-dot mode, then changes timing for the screen it is about to show.

## SDK mode selection

The LLVM-MOS PCE SDK declares pce_vdc_set_resolution(width, height, vce_flags), pce_vdc_set_width, and the pixel-clock constants in pce/vdc.h and pce/hardware.h. A simple project can use the SDK helper after disabling display output and before uploading the BAT, patterns, or SAT:

    pce_vdc_set_resolution(320, 224, VCE_PIXEL_CLOCK_7MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_64_32);

For a 512-dot viewport, use the 10 MHz setting and at least a 64-character visible BAT row:

    pce_vdc_set_resolution(512, 224, VCE_PIXEL_CLOCK_10MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_128_64);

Check the installed SDK version's declarations before copying calls. Keep the video off while changing timing and VRAM layout. Configure the VDC's VBlank/SAT path and IRQ handlers before enabling the display.

## Register settings used by Saber Rider

The front-end helper video_mode_ui() writes VCE control 1, HSR 0x0503, HDR 0x0627, VPR 0x1702, VDW 223, and VCR 12. HDR's low field selects 40 character cells across. It also disables DMA and selects VDC memory mode 0x0010.

The race helper timing(true) writes VCE control 2, HSR 0x0b02, HDR 0x043f, VPR 0x1702, VDW 223, and VCR 12. HDR's low field selects 64 character cells across. video_race_init() then selects VDC BG size 128 by 64 and enables the raster path. The 128-character virtual map supplies the road and its wrap copies; the display exposes a 512-dot viewport into it.

The race path sets HBlank interrupts and updates BXR/BYR at band boundaries. Do not replace that setup with a one-time mode call and expect the road to work: it depends on the raster IRQ, road tables, VBlank page handoff, and the exact map layout.

## Adaptation checklist

- Rebuild or bake screen art at the intended dot width. The 320-dot frontend and 512-dot race do not share the same screen-space clipping limits.
- Set the BAT virtual width independently from the visible width. A 512-dot display needs 64 visible 8-dot cells, while a 128-cell BAT may still be useful for the scrolling world.
- Recheck sprite placement, scanline admission, HUD margins, and the visible result in the target emulator. At 512 dots the pixel clock changes; it is not a software stretch of the 320-dot image.
- Change VCE/VDC timing at a safe transition with display output blanked. Publish the new SAT and scroll state before turning the new screen on.
- Keep 224-line timing only when it matches the project and target region. PAL and overscan decisions are separate from horizontal mode selection.

## Saber Rider trace

The reference implementation is in Saber Rider's PCE video code: video_init(), video_mode_ui(), timing(), and video_race_init() in src/platform/pce/video_pce.c. Race 2 reaches the 512-dot setup through the race field initialization in src/platform/pce/road_pce.c. The racing IRQ changes are in src/platform/pce/irq.S.
