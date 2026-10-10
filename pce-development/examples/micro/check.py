#!/usr/bin/env python3
"""Lint the tiny examples, optionally build every independent HuCard ROM.

python3 check.py             # lint and build every micro ROM
python3 check.py --lint-only # static checks; does not require LLVM-MOS
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
AUDIO_FORBIDDEN = (
    'pce_vdc', 'pce_vce', 'IO_VDC', 'IO_VCE', 'pce_sgx_vdc',
    'demo_video', 'draw_text', 'graphics_init', 'gfx.h', 'sprite_',
    'IO_PCD_ADPCM', 'printf(', 'puts(',
)
VIDEO_FORBIDDEN = ('pce_psg', 'IO_PSG', 'PSG_CH_', 'tone_init(', 'psg.h')


def lint(project):
    problems = []
    main = project / 'main.c'
    readme = project / 'README.md'
    makefile = project / 'Makefile'
    for path in (main, readme, makefile):
        if not path.is_file():
            problems.append(f'{path.name}: missing')
    if problems:
        return problems

    source = main.read_text()
    doc = readme.read_text()
    if makefile.read_text().strip() != 'include ../common.mk':
        problems.append('Makefile must use the shared one-line build rule')
    if len(source.splitlines()) > 45:
        problems.append('main.c is longer than 45 lines; split the lesson')

    if '**Audio:**' in doc:
        # Audio is deliberately allowed to be silent *visually*. No borrowed
        # graphics helpers, fonts, VDC IRQs, palette indicators or HUDs.
        used = [term for term in AUDIO_FORBIDDEN if term in source]
        if used:
            problems.append(f'audio and graphics mixed: {used}')
        if any(child.name.startswith('demo_video') for child in project.iterdir()):
            problems.append('audio project contains a video fixture')
    if '**Graphics:**' in doc:
        used = [term for term in VIDEO_FORBIDDEN if term in source]
        if used:
            problems.append(f'graphics project contains audio code: {used}')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lint-only', action='store_true')
    args = parser.parse_args()
    projects = sorted(p for p in ROOT.iterdir() if p.is_dir() and (p / 'Makefile').exists())
    failures = []
    for project in projects:
        for issue in lint(project):
            failures.append(f'{project.name}: {issue}')

    # The two older *audio* recipes must also remain completely nonvisual.
    examples = ROOT.parent
    for name in ('05-sound-samples', '24-hardware-adpcm-and-psg-dda'):
        project = examples / name
        if any((project / 'src').glob('demo_video*')):
            failures.append(f'{name}: unexpected video fixture')
        for src in sorted((project / 'src').glob('*.c')):
            used = [term for term in AUDIO_FORBIDDEN if term in src.read_text()]
            if used:
                failures.append(f'{name}/{src.name}: audio/video mixing {used}')

    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print(f'PASS: {len(projects)} single-purpose source checks plus both legacy audio recipes', flush=True)
    if args.lint_only:
        return 0

    failed_builds = []
    for project in projects:
        cmd = ['make', '-s', '--no-print-directory']
        run = subprocess.run(cmd, cwd=project, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        print(('OK   ' if run.returncode == 0 else 'FAIL ') + project.name, flush=True)
        if run.returncode:
            failed_builds.append(f'{project.name}: {run.stdout[-2500:]}')
    if failed_builds:
        print('\n'.join(failed_builds), file=sys.stderr)
        return 1
    print(f'PASS: {len(projects)}/{len(projects)} micro ROMs built', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
