#!/usr/bin/env python3
"""Reproducible comparison of two NON-ATOMIC 128x128 VRAM DMA presenters."""
import argparse
import json
from pathlib import Path


def compare(status, irq, visual):
    if not visual.get('matched') or visual.get('differing_pixels') != 0:
        raise ValueError('settled screenshots differ')
    if status['totals']['video_frames'] != irq['totals']['video_frames']:
        raise ValueError('different benchmark video durations')
    for original, changed in zip(status['scenario'], irq['scenario']):
        if original['segment'] != changed['segment'] or original['emulator_frames'] != changed['emulator_frames']:
            raise ValueError('different controller scenario')
    return {
        'passed': True,
        'resolution': [128, 128],
        'status_polling_turning_presentations_per_second': status['totals']['turning_views_per_second'],
        'irq_completion_turning_presentations_per_second': irq['totals']['turning_views_per_second'],
        'status_polling_total_presentations': status['totals']['changed_views'],
        'irq_completion_total_presentations': irq['totals']['changed_views'],
        'exact_settled_image': True,
        'differing_physical_pixels': visual['differing_pixels'],
        'notes': ['Both buffered variants still copy the BAT in two separate 4096-word DMA transfers.',
                  'Completed DMA presentations are not proof of tear-free frames or hardware timing.',
                  'Do not infer an FPS win from a changed game-loop update count.'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('polling', 'irq', 'visual', 'output'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    result = compare(*[json.loads(Path(getattr(args, k)).read_text()) for k in ('polling', 'irq', 'visual')])
    Path(args.output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f'VDC completion comparison FAIL: {exc}')
