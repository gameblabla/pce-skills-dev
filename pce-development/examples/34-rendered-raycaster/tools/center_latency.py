#!/usr/bin/env python3
"""Compare central-view response time with the full-detail linear scheduler.

Both ROMs use the same 128 rays, 96-word VBlank limit and art. Complete-view
throughput is a separate metric; this test checks how quickly the central
128 physical screen pixels become correct after a discrete camera turn.
"""
import argparse
import json
from pathlib import Path

from PIL import Image
import genre_trace
import platformer_trace

WAIT_FRAMES = (0, 4, 12, 24, 40, 80, 160)
CENTER_BOX = (216, 53, 344, 198)  # center 128 physical pixels; exclude border


def capture(rom: Path, output: Path, label: str):
    binary = platformer_trace._find_binary(str(rom))
    client = platformer_trace.NativeControl(
        str(binary), str(rom), output.parent / (f'{output.stem}-{label}-rpc'), initial_frames=2)
    images = []
    try:
        client.call('input', 0)
        client.call('run', 220)
        before = output.parent / f'{output.stem}-{label}-before.png'
        # The headless frontend creates screenshots exclusively. Repeated
        # regression runs must remove their prior captures first.
        before.unlink(missing_ok=True)
        client.call('screenshot', str(before))
        images.append(Image.open(before).convert('RGB'))
        client.call('input', 1 << genre_trace.BUTTONS['right'])
        client.call('run', 6)
        client.call('input', 0)
        preceding = 0
        for frame in WAIT_FRAMES:
            if frame > preceding:
                client.call('run', frame - preceding)
            preceding = frame
            name = output.parent / f'{output.stem}-{label}-{frame:03d}.png'
            name.unlink(missing_ok=True)
            client.call('screenshot', str(name))
            images.append(Image.open(name).convert('RGB'))
    finally:
        client.close()
    return images


def difference(image_a, image_b, box=None):
    if image_a.size != image_b.size:
        raise ValueError('ROM screenshots have different dimensions')
    if box:
        image_a = image_a.crop(box)
        image_b = image_b.crop(box)
    return sum(a != b for a, b in zip(image_a.get_flattened_data(),
                                       image_b.get_flattened_data()))


def run(linear_rom: Path, center_rom: Path, output: Path):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    linear = capture(linear_rom.resolve(), output, 'linear')
    center = capture(center_rom.resolve(), output, 'center')
    if difference(linear[0], center[0]):
        raise ValueError('renderers do not share an identical initial image')
    if difference(linear[-1], center[-1]):
        raise ValueError('renderers do not converge to identical final RGB pixels')
    final = linear[-1]
    rows = []
    for index, frame in enumerate(WAIT_FRAMES):
        rows.append({
            'frames_after_turn': frame,
            'linear_center_differing_pixels': difference(linear[index + 1], final, CENTER_BOX),
            'center_first_differing_pixels': difference(center[index + 1], final, CENTER_BOX),
        })
    # The native ST0 VDC uploader can make both orders converge earlier.
    # Measure the first clean checkpoint rather than locking the threshold
    # to the historical frame-40/frame-80 results.
    def first_clean(key):
        return next((r['frames_after_turn'] for r in rows
                     if r[key] == 0), None)
    center_at=first_clean('center_first_differing_pixels')
    linear_at=first_clean('linear_center_differing_pixels')
    if center_at is None or linear_at is None or not center_at < linear_at:
        raise ValueError(f'center-first latency advantage not demonstrated: {rows}')
    report = {
        'passed': True,
        'resolution': [128, 128],
        'metric': 'RGB mismatch against settled screenshot in central 128x145 physical pixels',
        'note': 'Perceptual center latency, not completed full-view FPS',
        'checkpoints': rows,
        'center_first_settled_by_frame': center_at,
        'linear_settled_by_frame': linear_at,
        'final_differing_pixels': difference(linear[-1], center[-1]),
    }
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--linear-rom', required=True, type=Path)
    p.add_argument('--center-rom', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    try:
        run(args.linear_rom, args.center_rom, args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    main()
