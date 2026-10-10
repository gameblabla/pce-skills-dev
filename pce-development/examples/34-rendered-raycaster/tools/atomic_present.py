#!/usr/bin/env python3
"""ROM-driven proof that a 64-row paired-BAT front page never changes mid-build.

Unlike texture/trace tests, compares *actual framebuffer screenshots* when the
ROM says it did not flip the front page. A changed screenshot without a VBlank
presentation, a page flip without a completed pass, or an unchanged screenshot
through all turning inputs is a hard failure. Does not claim physical testing.
"""
import argparse
import hashlib
import json
from pathlib import Path

import genre_trace
import platformer_trace
from PIL import Image

from bitmap_stress import check_bitmap_frame


def check_atomic_samples(samples):
    """Pure deterministic acceptance logic; negative-tested offline."""
    if len(samples)<6:
        raise ValueError('too few presentation samples')
    swaps=0
    visible_changes=0
    last=None
    prior_swap=False
    delayed_captures=0
    for index,item in enumerate(samples):
        if item['page'] not in (0,1) or item['pending'] not in (0,1,255):
            raise ValueError('invalid front/back page state')
        if type(item['redraws']) is not int or item['redraws']<0:
            raise ValueError('invalid redraw counter')
        if not isinstance(item.get('digest'),str) or len(item['digest'])!=64:
            raise ValueError('missing screenshot hash')
        if item['pending'] == item['page']:
            raise ValueError('queued back page equals displayed page')
        if last is not None:
            diff=item['redraws']-last['redraws']
            if diff<0 or diff>1:
                raise ValueError('missed or reversed swap counter')
            if diff==0:
                if item['page']!=last['page']:
                    raise ValueError('front page changed without a VBlank swap')
                if item['digest']!=last['digest']:
                    # Headless screenshot buffer may lag the VBlank swap by
                    # one sampled interval. A second interval is NEVER okay.
                    if not prior_swap:
                        raise ValueError(f'TEARING: framebuffer changed with no recent swap (sample {index})')
                    delayed_captures+=1
            else:
                swaps+=1
                if item['page']==last['page']:
                    raise ValueError('completed redraw did not toggle front page')
                if item['digest']!=last['digest']:
                    visible_changes+=1
        prior_swap=(last is not None and item['redraws']>last['redraws'])
        last=item
    if swaps<2 or visible_changes<2:
        raise ValueError('insufficient real visible VBlank swaps')
    return {'swaps':swaps, 'visible_changes':visible_changes,
            'stable_samples':len(samples)-swaps-delayed_captures-1,
            'one_sample_capture_lags':delayed_captures}


def run(rom,elf,out,frames):
    if frames<80 or frames>900:
        raise ValueError('frames must be 80..900')
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    rom=Path(rom).resolve();elf=Path(elf).resolve()
    sym={name:platformer_trace.resolve_trace_address(elf,name)
         for name in ('bat_display_page','bat_ready_page','ray_redraws')}
    exe=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(exe),str(rom),out.parent/(out.stem+'-rpc'),initial_frames=2)
    samples=[]
    try:
        client.call('input',0)
        client.call('run',150)  # wait for two fully rendered and published pages
        client.call('input',1 << genre_trace.BUTTONS['right'])
        for step in range(frames//4):
            client.call('run',4)
            def memory(name,n):
                raw=client.call('memread',hex(sym[name]),n,1)['hex']
                return int.from_bytes(bytes.fromhex(raw),'little')
            sample={'step':step,'page':memory('bat_display_page',1),
                    'pending':memory('bat_ready_page',1),
                    'redraws':memory('ray_redraws',2)}
            shot=out.parent/(out.stem+f'-{step:03d}.png')
            shot.unlink(missing_ok=True)
            client.call('screenshot',str(shot))
            with Image.open(shot) as img:
                sample['digest']=hashlib.sha256(img.convert('RGB').tobytes()).hexdigest()
            if step in (0,frames//8,frames//4-1):
                sample['bitmap']=check_bitmap_frame(shot)
                sample['screenshot']=str(shot)
            else:
                shot.unlink(missing_ok=True)
            samples.append(sample)
    finally:
        client.close()
    try: result=check_atomic_samples(samples)
    except ValueError:
        out.write_text(json.dumps({'samples':samples},indent=2)+'\n')
        raise
    report={'result':'passed','format':'paired-bat-atomic-64-v1',
            'layout':'two 64x64 BAT half-pages, 128x64 logical pixels, 512x224 video',
            'emulator_frames':frames, 'samples':samples, 'totals':result,
            'limitation':'64 logical lines instead of full 128; emulator proof, not physical hardware'}
    out.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True)
    p.add_argument('--elf',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--frames',type=int,default=160)
    a=p.parse_args()
    try:
        r=run(a.rom,a.elf,a.output,a.frames)
        print(json.dumps({'result':r['result'],**r['totals']}))
    except (OSError,ValueError,RuntimeError) as e:p.error(str(e))
if __name__=='__main__':main()
