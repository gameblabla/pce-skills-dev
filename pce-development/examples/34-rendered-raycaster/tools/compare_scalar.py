#!/usr/bin/env python3
"""Compare IRQ-bounded scalar tail transfers with identical full-detail art.

Both ROMs keep generated 8-word wall code and 128x128 BAT geometry. The
reference uses TIA for 1..8-word scalar gaps and the original depth key;
the optimized ROM writes these short gaps directly and uses the canonical
wall-image key. The test measures ROM-owned dirty-view and VDC word counters,
checks twelve emulator images, and separately validates a stationary image.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from column_benchmark import run as benchmark
from wall_equivalence import run as compare_images


def compare(reference, optimized):
    a=reference['scenario'];b=optimized['scenario']
    if len(a)!=6 or len(a)!=len(b):
        raise ValueError('both complete six-part input scenarios are required')
    rows=[]
    for x,y in zip(a,b):
        if x['segment']!=y['segment'] or x['emulator_frames']!=y['emulator_frames'] or x['buttons']!=y['buttons']:
            raise ValueError('controller schedule differs')
        for sample in (x,y):
            if sample['screenshot_colors']<5 or sample['game_updates']<=0:
                raise ValueError('blank/stalled scene')
        rows.append({'segment':x['segment'],'video_frames':x['emulator_frames'],
                     'reference_changed_views':x['dirty_views'],'optimized_changed_views':y['dirty_views'],
                     'reference_updates':x['game_updates'],'optimized_updates':y['game_updates'],
                     'reference_bat_words':x['vram_words'],'optimized_bat_words':y['vram_words']})
    r=reference['totals']['turning_views_per_second']
    o=optimized['totals']['turning_views_per_second']
    if not r or o<r:
        raise ValueError('short-span optimization regressed measured turning throughput')
    return {'passed':True,'logical_resolution':[128,128],'reference_turning_views_per_second':r,
            'optimized_turning_views_per_second':o,'improvement_pct':round((o/r-1)*100,2),
            'segments':rows,
            'limitations':['Same video-frame/controller budget, NOT guaranteed identical game positions',
                           'Completed dirty-column views, NOT atomic full-frame swaps',
                           'Emulated timing only; real-hardware results unmeasured']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True);p.add_argument('--optimized',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    a=benchmark(args.reference,str(args.reference)+'.elf',output.with_name('scalar-tia-benchmark.json'))
    b=benchmark(args.optimized,str(args.optimized)+'.elf',output.with_name('scalar-direct-benchmark.json'))
    result=compare(a,b)
    result['stationary_image']=compare_images(args.reference,args.optimized,
                                              output.with_name('scalar-stationary-equivalence.json'))
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'reference_views_per_second':result['reference_turning_views_per_second'],
                      'optimized_views_per_second':result['optimized_turning_views_per_second'],
                      'improvement_pct':result['improvement_pct'],
                      'stationary':result['stationary_image']['evidence']},indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,RuntimeError) as e:raise SystemExit(f'scalar FPS FAIL: {e}')
