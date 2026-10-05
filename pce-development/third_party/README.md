# Third-party emulator source

This bundle contains the supplied Mednafen PCE Dev source snapshot, its build scripts, headless build notes, MCP wrapper, upstream documentation, and component license notices. Source and documentation were copied unchanged. Locally generated object files, libraries, configured build files, and emulator executables were omitted.

The generated `mednafen/po/Makefile.in` is omitted with the other configured files; its source template, `mednafen/po/Makefile.in.in`, is included.

For the headless frontend, start with [`mednafenPceDev-main/README_HEADLESS.md`](mednafenPceDev-main/README_HEADLESS.md). The main Mednafen license is at [`mednafenPceDev-main/mednafen/COPYING`](mednafenPceDev-main/mednafen/COPYING); retain all vendored component notices. The MCP server source is [`mednafenPceDev-main/mednafen/src/drivers_libxxx/mcp_server.py`](mednafenPceDev-main/mednafen/src/drivers_libxxx/mcp_server.py).
