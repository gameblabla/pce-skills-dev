#!/usr/bin/env python3
"""Compare identical 128x128 camera scenarios and exact screenshots.

An identical dirty-view rate is not an FPS speedup. Report the incremental
VDC-register-work elimination separately from whole-view throughput.
"""
import argparse
import json
from pathlib import Path


def compare(old, new, visual):
    if not visual['matched'] or visual['differing_pixels']!=0:
        raise ValueError('presentation changed screen pixels')
    a=old['scenario'];b=new['scenario']
    if len(a)!=len(b):raise ValueError('unequal controller segments')
    segments=[]
    for x,y in zip(a,b):
        if x['buttons']!=y['buttons'] or x['emulator_frames']!=y['emulator_frames']:
            raise ValueError('camera scenarios differ')
        segments.append({'segment':y['segment'],
                         'old_dirty_views':x['dirty_views'],'new_dirty_views':y['dirty_views'],
                         'old_vram_words':x['vram_words'],'new_vram_words':y['vram_words'],
                         'old_game_updates':x['game_updates'],'new_game_updates':y['game_updates']})
    ot=old['totals'];nt=new['totals']
    if nt['changed_views']<ot['changed_views'] or nt['turning_views_per_second']<ot['turning_views_per_second']:
        raise ValueError('presentation regresses completed dirty views')
    return {'passed':True,'resolution':[128,128],
            'old_dirty_views':ot['changed_views'],'new_dirty_views':nt['changed_views'],
            'old_turning_views_per_second':ot['turning_views_per_second'],
            'new_turning_views_per_second':nt['turning_views_per_second'],
            'old_vram_words':ot['vram_words'],'new_vram_words':nt['vram_words'],
            'same_final_pixels':visual['matched'],
            'compared_rgb_pixels':visual['pixel_count'],
            'segments':segments,
            'interpretation':'MAWR address reprogramming is omitted for contiguous, 8-word vertical bursts. This reduces register traffic, not the number of transferred BAT words. It is not a demonstrated full-screen FPS gain.',
            'limits':['Emulated timings, not physical-hardware measurements','No atomic swaps; view commits are progressive dirty-column passes']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',required=True);p.add_argument('--new',required=True)
    p.add_argument('--visual',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    with open(a.old) as f: old=json.load(f)
    with open(a.new) as f: new=json.load(f)
    with open(a.visual) as f:visual=json.load(f)
    result=compare(old,new,visual)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('segments','limits','interpretation')},indent=2))

if __name__=='__main__':main()
