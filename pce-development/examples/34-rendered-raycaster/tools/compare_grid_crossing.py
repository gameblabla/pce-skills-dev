#!/usr/bin/env python3
"""Compare exact Q8 marcher and optional empty-grid intercept skip.

Only report genuine completed dirty-view and VRAM-word totals. These are
progressive view commits, not independent 128x128 full-screen frames.
"""
import argparse
import json
from pathlib import Path


def compare(stable,experimental,visual,raster,stress):
    a=stable['scenario'];b=experimental['scenario']
    assert len(a)==len(b)==6
    for ref,opt in zip(a,b):
        if (ref['segment'],ref['emulator_frames'],ref['buttons']) != (opt['segment'],opt['emulator_frames'],opt['buttons']):
            raise ValueError('controller scenario or emulator window changed')
    # Held-input scenarios may process different numbers of game-loop
    # iterations: do not claim equal-work CPU timing from these counters.
    if stable['totals']['vram_words'] != experimental['totals']['vram_words']:
        raise ValueError('uploaded BAT word totals differ')
    if not visual['matched'] or visual['differing_pixels']:
        raise ValueError('stationary images changed')
    if not raster['passed'] or not stress['totals']['changed_views']>=1:
        raise ValueError('raster or sustained movement regression')
    return {
        'result':'passed',
        'name':'VCS-inspired grid boundary tracking with exact Q8 empty-cell skips',
        'benchmark_video_frames':stable['totals']['video_frames'],
        'reference_game_updates':sum(row['game_updates'] for row in a),
        'experimental_game_updates':sum(row['game_updates'] for row in b),
        'reference_dirty_views':stable['totals']['changed_views'],
        'experimental_dirty_views':experimental['totals']['changed_views'],
        'reference_turning_commits_per_second':stable['totals']['turning_views_per_second'],
        'experimental_turning_commits_per_second':experimental['totals']['turning_views_per_second'],
        'reference_vram_words':stable['totals']['vram_words'],
        'experimental_vram_words':experimental['totals']['vram_words'],
        'stationary_pixel_differences':visual['differing_pixels'],
        'raster_frames':raster['emulator_frames'],
        'midpoint_floor_similarity':raster['highest_midpoint_floor_similarity'],
        'movement_frames':stress['totals']['emulator_frames'],
        'movement_dirty_views':stress['totals']['changed_views'],
        'interpretation':'No measurable completed-view FPS benefit. Keep the original caster as the production default; optional experiment only.'
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','experimental','visual','raster','stress','output'):
        p.add_argument('--'+name,required=True)
    args=p.parse_args()
    docs=[json.loads(Path(getattr(args,name)).read_text()) for name in ('reference','experimental','visual','raster','stress')]
    result=compare(*docs)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
