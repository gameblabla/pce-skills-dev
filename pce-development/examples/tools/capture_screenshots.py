#!/usr/bin/env python3
"""Build numbered examples and capture actual ROM output with headless Mednafen."""
import argparse
import json
from urllib.parse import quote
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMULATOR = ROOT.parent / 'third_party/mednafenPceDev-main/mednafen/src/mednafen-pce-headless'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, default=DEFAULT_EMULATOR)
    parser.add_argument('--frames', type=int, default=120)
    parser.add_argument('--example', type=int, choices=range(25))
    args = parser.parse_args()
    emulator = args.emulator.resolve()
    if not emulator.is_file():
        parser.error('build the bundled headless emulator or pass --emulator PATH')
    if args.frames <= 0:
        parser.error('--frames must be positive')
    for folder in sorted(ROOT.glob('[0-9][0-9]-*')):
        if args.example is not None and int(folder.name[:2]) != args.example:
            continue
        build = subprocess.run(['make'], cwd=folder, capture_output=True, text=True)
        if build.returncode:
            raise RuntimeError(f'{folder.name}: build failed\n{build.stdout}\n{build.stderr}')
        # The emulator refuses to overwrite existing PNG files. Capture to a
        # fresh path, then replace the checked-in image only after success.
        with tempfile.TemporaryDirectory(dir=folder / 'build') as scratch:
            output = Path(scratch) / 'screenshot.png'
            # Set released buttons explicitly for a reproducible idle frame.
            commands = f'input\t0\nrun\t{args.frames}\nscreenshot\t{quote(str(output))}\nquit\n'
            capture = subprocess.run([str(emulator), '--rom', str(folder / 'build' / (folder.name+'.pce')),
                                      '--frames', '0', '--rpc'], input=commands,
                                     cwd=scratch, capture_output=True, text=True)
            replies = [json.loads(line) for line in capture.stdout.splitlines() if line.startswith('{')]
            if (capture.returncode or len(replies) != 4 or
                    any(not reply.get('ok') for reply in replies) or not output.is_file()):
                raise RuntimeError(f'{folder.name}: capture failed\n{capture.stdout}\n{capture.stderr}')
            shutil.copyfile(output, folder / 'assets/screenshot.png')
        print(f'{folder.name}: built and captured {args.frames} frames', flush=True)


if __name__ == '__main__':
    main()
