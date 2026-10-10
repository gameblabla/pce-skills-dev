#!/usr/bin/env python3
"""Lint the tiny examples, optionally build every independent HuCard ROM.

python3 check.py             # lint and build every micro ROM
python3 check.py --lint-only # static checks; does not require LLVM-MOS
"""
import argparse
import re
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
KNOWN_CATEGORIES = {'Audio', 'Graphics', 'CPU', 'CPU/IRQ', 'Input', 'SuperGrafx', 'Arcade Card'}
NONVISUAL = {'Audio', 'CPU', 'CPU/IRQ', 'Input', 'Arcade Card'}


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
    if any(project.glob('*.h')) or len(list(project.glob('*.c'))) != 1:
        problems.append('project must have just main.c; place reusable helpers beside common.mk')
    if len(source.splitlines()) > 45:
        problems.append('main.c is longer than 45 lines; split the lesson')

    # Never infer the project type from optional prose. Every README has an
    # explicit category, otherwise the previous audio/video guard was skipped.
    category_match = re.search(r'^\*\*Category:\*\*\s*(.+?)\s*$', doc, re.MULTILINE)
    category = category_match.group(1) if category_match else None
    if category not in KNOWN_CATEGORIES:
        problems.append(f'unknown or missing Category: {category!r}')
    if category in NONVISUAL:
        used = [term for term in AUDIO_FORBIDDEN if term in source]
        if used:
            problems.append(f'nonvisual project contains display code: {used}')
        if any(child.name.startswith('demo_video') for child in project.iterdir()):
            problems.append('nonvisual project contains a video fixture')
    if category in ('Graphics', 'SuperGrafx'):
        used = [term for term in VIDEO_FORBIDDEN if term in source]
        if used:
            problems.append(f'graphics project contains audio code: {used}')
    if category == 'Audio' and 'sprite.h' in source:
        problems.append('audio project must not import the sprite helper')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lint-only', action='store_true')
    parser.add_argument('--smoke', action='store_true',
                        help='run and inspect silent audio, visible sprite, and filled bitmap ROMs')
    parser.add_argument('--self-test', action='store_true',
                        help='prove that deliberate audio/video mixing is rejected')
    args = parser.parse_args()
    if args.self_test:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            for category, injected in [('Audio', 'pce_vdc_bg_enable();'),
                                       ('Graphics', '*IO_PSG_VOLUME = 0xff;'),
                                       ('Input', 'graphics_init();')]:
                sample = Path(tmp) / category
                sample.mkdir()
                (sample / 'main.c').write_text('#include <pce.h>\nint main(void){'+injected+'}')
                (sample / 'Makefile').write_text('include ../common.mk\n')
                (sample / 'README.md').write_text('**Category:** '+category+'\n')
                if not lint(sample):
                    print(f'FAIL: invalid {category} example passed lint', file=sys.stderr)
                    return 1
            print('PASS: deliberate audio/video mixing rejected for three project types')
        return 0
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
    if args.smoke:
        try:
            from PIL import Image
        except ImportError:
            print('Pillow required for screenshot smoke checks (pip install Pillow)', file=sys.stderr)
            return 1
        for name, should_be_visible in [('63-psg-quarter-pulse', False),
                                        ('78-vdc-one-sprite', True),
                                        ('85-bitmap-128-circle', True),
                                        ('86-mode7-bitmap-floor', True)]:
            project = ROOT / name
            run = subprocess.run(['make', '-s', 'run'], cwd=project,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            image_path = project / 'build' / 'headless.png'
            if run.returncode or not image_path.is_file():
                print(f'FAIL: emulator smoke test {name}: {run.stdout[-1200:]}', file=sys.stderr)
                return 1
            with Image.open(image_path) as screen:
                rgb = screen.convert('RGB')
                colors = rgb.getcolors(maxcolors=512)
                unique = len(colors) if colors is not None else 513
                center = rgb.crop((rgb.width // 2 - 24, rgb.height // 2 - 24,
                                   rgb.width // 2 + 24, rgb.height // 2 + 24))
                center_colors = center.getcolors(maxcolors=512)
                if name == '78-vdc-one-sprite' and (unique < 3 or (center_colors is not None and len(center_colors) < 2)):
                    print(f'FAIL: sprite example drew no visible sprite: {image_path}', file=sys.stderr)
                    return 1
                if not should_be_visible and unique != 1:
                    print(f'FAIL: audio example drew graphics: {image_path}', file=sys.stderr)
                    return 1
                if name in ('85-bitmap-128-circle', '86-mode7-bitmap-floor'):
                    # Prevent regression to partially transferred tiles: a red
                    # crescent can compile and run while most pixels are black.
                    red = [(x, y) for y in range(rgb.height) for x in range(rgb.width)
                           if (lambda p: p[0] > 128 and p[0] > 2*p[1] and
                               p[0] > 2*p[2])(rgb.getpixel((x, y)))]
                    if len(red) < 2000 or not red:
                        print(f'FAIL: bitmap output missing filled red shape: {image_path}', file=sys.stderr)
                        return 1
                    left, right = min(x for x, _ in red), max(x for x, _ in red)
                    top, bottom = min(y for _, y in red), max(y for _, y in red)
                    if right - left < 50 or bottom - top < 50:
                        print(f'FAIL: bitmap shape is unexpectedly small: {image_path}', file=sys.stderr)
                        return 1
            print(f'PASS: emulator screenshot {name} ({unique} colors)', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
