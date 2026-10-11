#!/usr/bin/env python3
"""Repeated mixed-input PCE screenshot stress for the natural-scroll IRQ.

Unlike the ordinary six-checkpoint test, this repeats movement and turning
through several complete circuits and verifies independent pixels and progress
at every checkpoint. It does not claim physical hardware timing safety.
"""
import argparse
import json
from pathlib import Path

import genre_trace
import platformer_trace
from bitmap_stress import STEPS, check_bitmap_frame
from raster_sweep import midpoint_seam_metrics
from PIL import Image
from collections import Counter


def close_wall_visible(near_depth, colors, wall_colors):
    """Close-range coverage can hide the usual sky/floor palette variety."""
    return near_depth<=2 and colors>=5 and wall_colors>=2


def run(rom, elf, output, repeats=4):
    if not 1 <= repeats <= 12:
        raise ValueError('repeats must be 1..12')
    rom=Path(rom).resolve()
    output=Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    trace_address=platformer_trace.resolve_trace_address(elf, 'pce_genre_trace')
    redraw_address=platformer_trace.resolve_trace_address(elf, 'ray_redraws')
    emulator=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(emulator), str(rom),
                output.parent/(output.stem+'-rpc'), initial_frames=2)
    updates_previous=-1
    views_previous=-1
    results=[]
    try:
        for lap in range(repeats):
            for step,(frames,buttons) in enumerate(STEPS):
                mask=sum(1<<genre_trace.BUTTONS[k] for k in buttons)
                client.call('input',mask)
                client.call('run',frames)
                image_path=output.parent/(output.stem+f'-lap{lap}-step{step}.png')
                image_path.unlink(missing_ok=True)
                client.call('screenshot',str(image_path))
                raw=bytes.fromhex(client.call('memread',hex(trace_address),128,1)['hex'])
                trace=genre_trace.choose(raw)
                redraws=int.from_bytes(bytes.fromhex(
                    client.call('memread',hex(redraw_address),2,1)['hex']),'little')
                if trace['genre']!='raycaster' or (trace['buttons']&255)!=mask:
                    raise ValueError(f'input not acknowledged at lap {lap} step {step}')
                if trace['frame']<=updates_previous or redraws<views_previous:
                    raise ValueError(f'renderer stalled or counters regressed at lap {lap} step {step}')
                near_depth=trace['state'][2]>>6
                with Image.open(image_path) as opened:
                    im=opened.convert('RGB')
                    mid=midpoint_seam_metrics(im)
                    colors=len(im.getcolors(200000) or [])
                    wall_colors=len(Counter(im.crop((60,90,500,152)).get_flattened_data()))
                if mid['defective']:
                    raise ValueError(f'midpoint stripe at lap {lap} step {step}')
                # At ray depth 1 a flat close wall can hide sky/floor and
                # legitimately leave just five palette colors. The ordinary
                # bitmap checker assumes more distant geometry, so guard
                # close views separately rather than calling them blank.
                if near_depth<=2:
                    if not close_wall_visible(near_depth,colors,wall_colors):
                        raise ValueError(f'blank close-wall frame at lap {lap} step {step}')
                else:
                    try:
                        check_bitmap_frame(image_path,near_depth)
                    except ValueError as e:
                        raise ValueError(f'lap {lap} step {step}, near-depth={near_depth}: {e}') from e
                results.append({'lap':lap,'step':step,'input':list(buttons),
                                'updates':trace['frame'],'completed_views':redraws,
                                'near_depth':near_depth,
                                'midpoint_floor_similarity':mid['floor_copy'],
                                'colors':colors})
                updates_previous=trace['frame']
                views_previous=redraws
    finally:
        client.close()
    result={'passed':True,'repeats':repeats,'video_frames':sum(t[0] for t in STEPS)*repeats,
            'checkpoints':len(results),'game_updates':updates_previous,
            'completed_dirty_views':views_previous,'samples':results,
            'limitations':['emulated hardware only','dirty views are progressive updates, not full-screen FPS']}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True)
    p.add_argument('--elf',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--repeats',type=int,default=4)
    a=p.parse_args()
    try:
        run(a.rom,a.elf,a.output,a.repeats)
    except (ValueError,RuntimeError,OSError) as err:
        p.error(str(err))
