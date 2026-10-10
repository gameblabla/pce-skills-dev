#!/usr/bin/env python3
"""Independent VDC screenshot and finished-BAT-pass test (headless emulator).

Unlike G2TR's game-loop frame count, `ray_redraws` increments only AFTER the
final BAT row has been uploaded. Validate rendered screenshots at every sample
rather than trusting game-authored state to prove image correctness.
"""
import argparse
import json
from pathlib import Path

import genre_trace
import platformer_trace
from PIL import Image
from collections import Counter
from visual_scenario import check_pngs

# Captures cover static load, repeated turns and movement, not just one lucky
# completed image. Each segment is long enough to complete >1 full redraw.
STEPS=((180, ()), (180, ('right',)), (180, ('right',)),
       (180, ('up',)), (180, ('left',)), (180, ()))


def check_bitmap_frame(path):
    """Reject sky-only/blank VDC captures without assuming one wall material.

    Rotating a player can legitimately show only grey metal (as opposed to
    warm bricks). Require actual walls/floor, colour variation and no cyan;
    the stricter starter screenshot is separately covered by `bitmap-test`.
    """
    with Image.open(path) as raw:
        im=raw.convert('RGB')
    if im.size!=(560,242):
        raise ValueError('wrong PCE display size')
    colors=Counter(im.get_flattened_data())
    wall=Counter(im.crop((60,90,500,152)).get_flattened_data())
    floor=Counter(im.crop((40,172,520,221)).get_flattened_data())
    ceiling=Counter(im.crop((40,22,520,87)).get_flattened_data())
    if len(colors)<6 or len(ceiling)<2 or len(wall)<2 or len(floor)<2:
        raise ValueError('blank/partial bitmap: ceiling, wall or floor colour diversity absent')
    if sum(n for (r,g,b),n in floor.items() if r>g and g>=b)<2000:
        raise ValueError('floor absent in bitmap screenshot')
    if sum(n for (r,g,b),n in wall.items() if r>g or g>r or (r>45 and g>45))<2500:
        raise ValueError('wall absent in bitmap screenshot')
    if any(r<60 and g>120 and b>120 for r,g,b in colors):
        raise ValueError('cyan holes in bitmap')
    return {'passed':True,'colors':len(colors),'wall_colors':len(wall),
            'floor_colors':len(floor),'independent':'emulator pixels'}


def validate(samples, min_completed=1):
    if len(samples)!=len(STEPS):
        raise ValueError('missing bitmap stress capture')
    prev_updates=prev_redraws=0
    for index,sample in enumerate(samples):
        if sample['segment']!=index or sample['emulator_frames']!=STEPS[index][0]:
            raise ValueError('bitmap stress segment mismatch')
        redraws=sample['total_redraws'];updates=sample['game_updates']
        if type(redraws) is not int or type(updates) is not int or redraws<0 or updates<0:
            raise ValueError('invalid bitmap counters')
        if redraws-prev_redraws<min_completed:
            raise ValueError(f'bitmap stalled: segment {index} completed only {redraws-prev_redraws} redraws')
        if updates<=prev_updates:
            raise ValueError(f'game loop stalled during bitmap segment {index}')
        if sample.get('bitmap',{}).get('passed') is not True:
            raise ValueError(f'bitmap screenshot {index} not independently verified')
        prev_updates,prev_redraws=updates,redraws
    return {'completed_redraws':samples[-1]['total_redraws'],
            'game_updates':samples[-1]['game_updates'],
            'emulator_frames':sum(step[0] for step in STEPS)}


def run(rom,elf,out):
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    rom=Path(rom).resolve();elf=Path(elf).resolve()
    redraw_addr=platformer_trace.resolve_trace_address(elf,'ray_redraws')
    trace_addr=platformer_trace.resolve_trace_address(elf,'pce_genre_trace')
    exe=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(exe),str(rom),out.parent/(out.stem+'-rpc'),initial_frames=2)
    captures=[]
    try:
        for index,(frames,buttons) in enumerate(STEPS):
            mask=sum(1<<genre_trace.BUTTONS[key] for key in buttons)
            client.call('input',mask)
            client.call('run',frames)
            pic=out.parent/(out.stem+f'-{index}.png')
            pic.unlink(missing_ok=True)
            client.call('screenshot',str(pic))
            report=check_bitmap_frame(pic)
            count=bytes.fromhex(client.call('memread',hex(redraw_addr),2,1)['hex'])
            trace=bytes.fromhex(client.call('memread',hex(trace_addr),128,1)['hex'])
            frame=genre_trace.choose(trace)
            if frame['genre']!='raycaster' or (frame['buttons']&0xff)!=mask:
                raise ValueError('raycaster did not acknowledge scripted input')
            captures.append({'segment':index,'buttons':list(buttons),
                             'emulator_frames':frames,'total_redraws':int.from_bytes(count,'little'),
                             'game_updates':frame['frame'],'bitmap':report,'screenshot':str(pic)})
    finally:client.close()
    counts=validate(captures)
    changed=check_pngs(captures[0]['screenshot'],captures[2]['screenshot'],
                       {'min_colors_each':6,'min_changed_pixels':7000})
    report={'result':'passed','format':'paired-bat-completed-pass-v1',
            'rom':str(rom),'segments':captures,'totals':counts,
            'rotation_pixel_evidence':changed,
            'limitations':['HuC6280 emulation, not physical hardware',
                           'Finished BAT passes, not atomic full-screen swaps',
                           'Screenshots validate colours/textures, not all pixels']}
    out.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True)
    p.add_argument('--elf',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    try:
        result=run(args.rom,args.elf,args.output)
        print(json.dumps({'result':result['result'],**result['totals'],
                          'changed_pixels':result['rotation_pixel_evidence']['changed_pixels']}))
    except (ValueError,RuntimeError,OSError) as exc:p.error(str(exc))
if __name__=='__main__':main()
