#!/usr/bin/env python3
"""Check exact image and report frame-bounded IRQ presentation improvements.

View commits are progressive update passes, NOT complete-frame FPS. Equal
controller video intervals can advance to different game poses. IRQ ticks
must be separately measured using cycle_profile.py, not inferred from commits.
"""
import argparse
import json
from pathlib import Path


def compare(old, new, visual):
    if [(s['segment'], s['buttons'], s['emulator_frames']) for s in old['scenario']] != [
            (s['segment'], s['buttons'], s['emulator_frames']) for s in new['scenario']]:
        raise ValueError('controller scenarios are not comparable')
    if visual.get('matched') is not True or visual.get('differing_pixels') != 0:
        raise ValueError('stationary emulator pixels changed')
    a, b = old['totals'], new['totals']
    if b['turning_views_per_second'] < a['turning_views_per_second']:
        raise ValueError('turning dirty-view commits regressed')
    return {
        'passed': True,
        'logical_resolution': [128, 128],
        'old_turning_dirty_views_per_second': a['turning_views_per_second'],
        'new_turning_dirty_views_per_second': b['turning_views_per_second'],
        'old_dirty_views': a['changed_views'],
        'new_dirty_views': b['changed_views'],
        'old_bat_words': a['vram_words'],
        'new_bat_words': b['vram_words'],
        'old_game_updates': sum(s['game_updates'] for s in old['scenario']),
        'new_game_updates': sum(s['game_updates'] for s in new['scenario']),
        'different_stationary_rgb_pixels': visual['differing_pixels'],
        'pixel_count': visual['pixel_count'],
        'limitations': ['No physical hardware verification',
                        'Dirty-view commits are not full-screen FPS',
                        'Controller intervals are equal, camera poses need not be'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for x in ('old', 'new', 'visual', 'output'):
        p.add_argument('--' + x, required=True)
    a = p.parse_args()
    try:
        report = compare(*[json.loads(Path(getattr(a, x)).read_text())
                           for x in ('old', 'new', 'visual')])
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    except (ValueError, KeyError, OSError) as ex:
        p.error(str(ex))


if __name__ == '__main__':
    main()
