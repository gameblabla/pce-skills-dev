#!/usr/bin/env python3
"""Report fixed-video-frame throughput of paced and uninterrupted BAT streams.

A changed-view pass is a completed incremental update, not a full-screen FPS.
Report CPU/game-loop updates separately: counts can change with game state.
The test intentionally does not equate passes with identical work.
"""
import argparse
import json
from pathlib import Path


def compare(old, new, visual):
    a, b = old['scenario'], new['scenario']
    if [(r['segment'],r['buttons'],r['emulator_frames']) for r in a] != [
            (r['segment'],r['buttons'],r['emulator_frames']) for r in b]:
        raise ValueError('presentation benchmark scenarios differ')
    if not visual.get('matched') or visual.get('differing_pixels') != 0:
        raise ValueError('paced presentation must reproduce the exact stationary image')
    turning_old=old['totals']['turning_views_per_second']
    turning_new=new['totals']['turning_views_per_second']
    if turning_new<turning_old:
        raise ValueError('paced BAT presentation regressed turning commits')
    return {
        'passed':True,'comparison':'same video-frame controller segments, not equal-work camera poses',
        'logical_resolution':[128,128],
        'turning_dirty_views_per_second':{'uninterrupted':turning_old,'paced':turning_new},
        'total_dirty_views':{'uninterrupted':old['totals']['changed_views'],
                             'paced':new['totals']['changed_views']},
        'bat_words':{'uninterrupted':old['totals']['vram_words'],
                     'paced':new['totals']['vram_words']},
        'game_updates':{'uninterrupted':sum(r['game_updates'] for r in a),
                        'paced':sum(r['game_updates'] for r in b)},
        'exact_stationary_rgb_pixels':visual['pixel_count'],
        'different_stationary_rgb_pixels':visual['differing_pixels'],
        'limitations':['Dirty-view passes are not atomic full-screen frames',
                       'Scripted input can advance to different poses when game updates differ',
                       'Results from HuC6280 emulation; physical PCE hardware unverified']
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',required=True);p.add_argument('--new',required=True)
    p.add_argument('--visual',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    try:
        old=json.loads(Path(a.old).read_text());new=json.loads(Path(a.new).read_text())
        visual=json.loads(Path(a.visual).read_text())
        result=compare(old,new,visual)
        Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,KeyError) as e:p.error(str(e))
if __name__=='__main__':main()
