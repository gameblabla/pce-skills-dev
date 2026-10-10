#!/usr/bin/env python3
"""Compare same-resolution C and generated-instruction VRAM column writers.

Do not equate ROM/game updates with identical game states: faster builds walk
farther for the same held-controller interval. Report actual frame, dirty-view,
and bus counters, plus static screenshot equivalence independently. This tool
raises for missing generated-code execution or degraded turning throughput.
"""
import argparse, json
from pathlib import Path
from column_benchmark import run as benchmark
from wall_equivalence import run as visual

def compare(ref,new):
    rows=[]
    for b,a in zip(ref['scenario'],new['scenario']):
        if a['segment'] != b['segment'] or a['emulator_frames'] != b['emulator_frames']:
            raise ValueError('benchmark scenario mismatch')
        rows.append({'segment':a['segment'],
                     'c_updates':b['game_updates'],'generated_updates':a['game_updates'],
                     'c_changed_views':b['dirty_views'],'generated_changed_views':a['dirty_views'],
                     'c_bat_words':b['vram_words'],'generated_bat_words':a['vram_words'],
                     'generated_asm_words':a['generated_words']})
    if any(x['generated_asm_words'] is None for x in rows):
        raise ValueError('generated ROM must publish actual microcode transfer counts')
    generated=sum(x['generated_asm_words'] for x in rows)
    uploaded=sum(x['generated_bat_words'] for x in rows)
    if generated<=0 or generated>=uploaded:
        raise ValueError('generated microcode never ran or falsely claimed all uploads')
    if any(x['generated_asm_words']%8 for x in rows):
        raise ValueError('generated path must publish whole eight-word bursts')
    if new['totals']['turning_views_per_second'] < ref['totals']['turning_views_per_second']:
        raise ValueError('generated wall writer regresses completed turning views')
    return {'passed':True,'segments':rows,'codegen_words':generated,
            'total_words':uploaded,
            'generated_fraction_of_uploaded_words':round(generated/uploaded,4),
            'c_turning_views_per_second':ref['totals']['turning_views_per_second'],
            'generated_turning_views_per_second':new['totals']['turning_views_per_second'],
            'c_game_updates':sum(s['game_updates'] for s in ref['scenario']),
            'generated_game_updates':sum(s['game_updates'] for s in new['scenario']),
            'limitation':'Same controller time, but different numbers of game updates and potentially different wall positions; NOT a fixed-work cycle comparison.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True);p.add_argument('--optimized',required=True);p.add_argument('--output',required=True)
    args=p.parse_args()
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    ref=benchmark(args.reference,str(args.reference)+'.elf',output.with_name('codegen-reference-stress.json'))
    new=benchmark(args.optimized,str(args.optimized)+'.elf',output.with_name('codegen-generated-stress.json'))
    c=compare(ref,new)
    c['visual']=visual(args.reference,args.optimized,output.with_name('codegen-exact-visual.json'))
    output.write_text(json.dumps(c,indent=2)+'\n')
    print(json.dumps({'passed':True,'codegen_words':c['codegen_words'],
        'fraction':c['generated_fraction_of_uploaded_words'],
        'C_turning_views_per_second':c['c_turning_views_per_second'],
        'generated_turning_views_per_second':c['generated_turning_views_per_second'],
        'exact_screenshot':c['visual']['matched']},indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError) as e:raise SystemExit(f'codegen benchmark FAIL: {e}')
