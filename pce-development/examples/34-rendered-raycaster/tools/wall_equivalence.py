#!/usr/bin/env python3
"""Check same-view screenshot EXACTNESS for legacy vs generated wall-pair shader.

Require an actual RPC-capable PC Engine emulator, two independent 128x128
full-detail HuCards, and matching colour pixels at the same idle view. It is
NOT a comparison to the separate half-height atomic renderer. Holding still
for 600 frames lets both progressive paths finish at least one complete BAT.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

from check_bitmap import check as check_bitmap
from platformer_trace import NativeControl, _find_binary


def compare_pixels(a, b):
    with Image.open(a) as first, Image.open(b) as second:
        first=first.convert('RGB');second=second.convert('RGB')
        if first.size!=(560,242) or second.size!=first.size:
            raise ValueError('both emulator captures must be 560x242')
        bbox=ImageChops.difference(first,second).getbbox()
        if bbox:
            raise ValueError(f'textured full-resolution bitmap changed: diff bounds {bbox}')
        return {'matched':True,'pixel_count':first.width*first.height,
                'evidence':'independent emulator screenshots; exact RGB equality'}


def capture(rom, dest, emulator, frames, base):
    dest=Path(dest);dest.unlink(missing_ok=True)
    client=NativeControl(str(emulator),str(Path(rom).resolve()),str(base),initial_frames=2)
    try:
        client.call('input',0)
        client.call('run',frames)
        client.call('screenshot',str(dest.resolve()))
    finally:
        client.close()
    check_bitmap(dest)


def run(reference, optimized, output, frames=600, emulator=None):
    if frames<512 or frames>2400:
        raise ValueError('need 512..2400 stationary emulator frames for complete full-resolution draws')
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if not Path(reference).is_file() or not Path(optimized).is_file():
        raise ValueError('two compiled full-detail HuCard ROMs are required')
    executable=emulator or _find_binary(str(reference))
    ref=output.with_name(output.stem+'-reference.png')
    new=output.with_name(output.stem+'-optimized.png')
    capture(reference,ref,executable,frames,output.parent/(output.stem+'-reference-rpc'))
    capture(optimized,new,executable,frames,output.parent/(output.stem+'-optimized-rpc'))
    result={'result':'passed','frames_each':frames,
            'full_detail_logical_pixels':[128,128],
            'reference_rom':str(Path(reference).resolve()),
            'optimized_rom':str(Path(optimized).resolve()),
            'reference_screenshot':str(ref),'optimized_screenshot':str(new),
            **compare_pixels(ref,new),
            'limitations':['Only a stationary rendered view; scripted input/throughput checked separately',
                           'Not a physical-console test; not comparable to 128x64 atomic screenshots']}
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True)
    p.add_argument('--optimized',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--frames',type=int,default=600)
    p.add_argument('--emulator')
    a=p.parse_args()
    try:print(json.dumps(run(a.reference,a.optimized,a.output,a.frames,a.emulator),indent=2))
    except (ValueError,OSError,RuntimeError) as e:p.error(str(e))

if __name__=='__main__':main()
