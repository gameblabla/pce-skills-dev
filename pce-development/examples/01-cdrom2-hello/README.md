# Example 01: CD-ROM² boot entry (HuCard preview)

The checked-in `src/main.c` demonstrates only that C `main` can be reached:
`booted` becomes 1 and the program loops. **No display, font, art, sprite,
or sound is initialized.** Read `booted` using a debugger. Run `make` to
compile the default HuCard preview `build/01-cdrom2-hello.pce`.

This **does not** boot from CD-ROM². A Super CD-ROM² application requires
the `mos-pce-cd-clang` application build, a System Card-compatible IPL,
sector-extent manifest, packaged disc image, and a compatible System Card
BIOS. Do not report a HuCard emulator run as a successful CD boot.

Once the CD boot path exists, verify each boundary separately: BIOS entry,
IPL read, application extent load, bank mapping, application jump, and finally
`booted` at the real application entry. Only add VCE/VDC initialization in a
**separate graphics example** when you actually want to draw a startup
screen; see [02-static-screen](../02-static-screen/README.md).
