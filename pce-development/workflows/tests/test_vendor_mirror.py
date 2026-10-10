"""Prevent the vendored Mednafen source and public include mirror drifting.

The historical copy of the emulator exposed older profiler and debug hooks in
include/mednafen while src/ had newer code. The mirror must be source-identical.
The test uses tracked file paths when Git is present, falling back to source
file extensions for a repository distributed without its .git directory.
"""

from pathlib import Path
import shutil
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[3]
MEDNAFEN = REPO / 'pce-development/third_party/mednafenPceDev-main/mednafen'
SOURCE = MEDNAFEN / 'src'
MIRROR = MEDNAFEN / 'include/mednafen'
PREFIX = 'pce-development/third_party/mednafenPceDev-main/mednafen/'


def _tracked_files():
    if shutil.which('git') and (REPO / '.git').exists():
        result = subprocess.run(
            ['git', '-C', str(REPO), 'ls-files', '-z', '--', PREFIX + 'src/',
             PREFIX + 'include/mednafen/'],
            capture_output=True, check=True,
        )
        paths = [Path(x.decode()) for x in result.stdout.split(b'\0') if x]
        source = set()
        mirror = set()
        for path in paths:
            text = path.as_posix()
            if text.startswith(PREFIX + 'src/'):
                source.add(text[len(PREFIX + 'src/'):])
            elif text.startswith(PREFIX + 'include/mednafen/'):
                mirror.add(text[len(PREFIX + 'include/mednafen/'):])
        return source, mirror

    # Sources extracted without Git: avoid build products such as .o and .deps.
    suffixes = {'.c', '.cpp', '.cc', '.h', '.hpp', '.inc', '.py', '.am', '.in'}
    def collect(root):
        return {p.relative_to(root).as_posix() for p in root.rglob('*')
                if p.is_file() and p.suffix in suffixes}
    return collect(SOURCE), collect(MIRROR)


class MednafenMirrorTests(unittest.TestCase):
    def test_source_mirror_matches_byte_for_byte(self):
        source, mirror = _tracked_files()
        self.assertGreater(len(source), 1400, 'Mednafen source files not found')
        self.assertEqual(source, mirror, 'Mednafen source/include file inventories differ')
        changed = [path for path in sorted(source)
                   if (SOURCE / path).read_bytes() != (MIRROR / path).read_bytes()]
        self.assertEqual(changed, [], f'Stale Mednafen source mirror: {changed[:20]}')


if __name__ == '__main__':
    unittest.main()
