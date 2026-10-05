# Third-party source

This folder contains the supplied PCE headless source snapshot, its build
scripts, headless frontend notes, MCP wrapper, upstream documentation, and
component license notices. Preserve all source licenses and notices. Locally
generated object files, libraries, configured build files, and executables are
not part of the skill bundle.

Start with the headless frontend notes in the source snapshot. The public skill
does not include a compiled binary, game ROM/disc image, or BIOS. Project Make
targets select the configured executable; keep source and executable details
inside the project helpers rather than coding-agent prompts.
