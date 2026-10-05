# Example 16: convert and display a static picture

**Build contract:** Copy the shared starter Makefile and tools. Install Python with NumPy and Pillow for the host converters. Display code must use the active project's VDC/Arcade RAM APIs; the asset outputs are raw binary with a JSON manifest.

The shared picture converter takes a PNG, fits tile-local colors into the PC Engine's 16 background palettes, converts pixels into four-plane 8 by 8 characters, deduplicates identical character patterns, emits BAT words, and writes a preview from the quantized output.

From the skill bundle root, a 320 by 224 Saber-style frontend image can be baked with:

    python3 pce-development/tools/pce/picture.py title.png --out build/title

The defaults match the Saber Rider front-end layout: a 320 by 224 canvas, a 64-character BAT row, and patterns starting at VDC word address 0x0800. A 512-dot image can use:

    python3 pce-development/tools/pce/picture.py race-title.png --canvas 512x224 --out build/race-title --pattern-word 0x0800 --bat-width 64

The tool writes patterns, palettes, BAT data, a decoded PNG preview, and a manifest. Use the manifest's byte lengths and address units when placing these files. The BAT output contains complete rows padded to the selected VDC BAT width; it does not include a runtime loader or choose addresses for other VRAM allocations.

## Runtime order

1. Blank the display and disable raster callbacks from the previous scene.
2. Select horizontal timing and BAT size for the image.
3. Upload the 16 background palettes and pattern bytes to the VCE/VRAM addresses named by the manifest.
4. Upload BAT rows using the VDC's configured row stride.
5. Set scroll to zero, submit an empty or matching SAT, then enable the background and display.

The Saber Rider UI loader follows this ordering in ui_show(): it disables video, sets 320-dot timing, uploads palettes, tile patterns, BAT rows and optional sprite patterns, submits the SAT, then allows the display to turn on. It reads generated assets from Arcade RAM. A scratch project can load files from disc instead, but should still stage data and validate each read before enabling the screen.

## Preview and failure checks

- Compare the emitted preview with the original and inspect the actual 9-bit VCE palette colors.
- Confirm that the BAT word's tile number points to the uploaded pattern base and that each row uses the configured BAT stride.
- Check palette 0 transparency/backdrop behavior, especially if the PNG has transparent pixels.
- Verify the final pattern and BAT writes stay inside the project's assigned VRAM ranges.
- Confirm the displayed result at both the intended width and the emulator's screenshot width; never infer that a 320-dot bake fits a 512-dot timing unchanged.
