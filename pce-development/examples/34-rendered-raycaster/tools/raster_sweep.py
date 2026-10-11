#!/usr/bin/env python3
"""Capture every video frame during sustained rotation to catch lost RCR IRQs.

The other end-to-end tests sample only at segment boundaries. A missing first
raster interrupt may produce one or two sky-only frames and then recover;
those must count as graphics failures rather than disappear between captures.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
import platformer_trace
import genre_trace


def run(rom, elf, output, frames=540, warmup=180):
    rom=Path(rom).resolve();output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    address=platformer_trace.resolve_trace_address(elf,'pce_genre_trace')
    binary=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(binary),str(rom),output.parent/(output.stem+'-rpc'),initial_frames=2)
    counts={};lowest=256;start=end=0
    frame=output.parent/(output.stem+'-latest.png')
    try:
        client.call('input',0)
        client.call('run',warmup)
        def progress():
            raw=bytes.fromhex(client.call('memread',hex(address),128,1)['hex'])
            return genre_trace.choose(raw)['frame']
        start=progress()
        client.call('input',1<<genre_trace.BUTTONS['right'])
        for i in range(frames):
            client.call('run',1)
            frame.unlink(missing_ok=True)
            client.call('screenshot',str(frame))
            with Image.open(frame) as raw:
                im=raw.convert('RGB')
                if im.size!=(560,242):raise ValueError('unexpected raster screenshot size')
                colors=len(im.getcolors(200000) or [])
            lowest=min(lowest,colors)
            counts[colors]=counts.get(colors,0)+1
            if colors<5:raise ValueError(f'sky-only or blank raster at turning frame {i+1}: {colors} colors')
        end=progress()
    finally: client.close()
    if end-start<frames//2:raise ValueError('rotation stress stalled game loop')
    report={'passed':True,'emulator_frames':frames,'warmup_frames':warmup,
            'minimum_colors':lowest,'color_counts':counts,'game_updates':end-start,
            'note':'all screenshots are native emulator pixels, not hardware validation'}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',required=True);parser.add_argument('--elf',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--frames',type=int,default=540)
    args=parser.parse_args()
    try:run(args.rom,args.elf,args.output,args.frames)
    except (ValueError,RuntimeError,OSError) as exc:parser.error(str(exc))
if __name__=='__main__':main()
