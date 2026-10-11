#!/usr/bin/env python3
"""Emulator regression for the opt-in 4-color genuine BAT page-switch mode.

Unlike completed-copy counters, ray_redraws increments only at the VBlank page
selection. Pixels must remain frozen between actual page selections.
"""
import argparse, json, hashlib
from pathlib import Path
from PIL import Image
import platformer_trace,genre_trace

def run(rom,elf,output,frames=540,warmup=180):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    exe=platformer_trace._find_binary(str(rom))
    redraw_address=platformer_trace.resolve_trace_address(elf,'ray_redraws')
    front_address=platformer_trace.resolve_trace_address(elf,'ray_flip_front')
    client=platformer_trace.NativeControl(str(exe),str(Path(rom).resolve()),output.parent/(output.stem+'-rpc'),initial_frames=2)
    prev=None;prev_flip=None;prev_front=None;num_flips=0;frozen=0;changes=0;min_colors=1000;max_floor_copy=0;last_flip_frame=-100
    photo=output.with_name(output.stem+'-latest.png')
    try:
        client.call('input',0);client.call('run',warmup)
        client.call('input',1<<genre_trace.BUTTONS['right'])
        for i in range(frames):
            client.call('run',1)
            photo.unlink(missing_ok=True);client.call('screenshot',str(photo))
            with Image.open(photo) as src:im=src.convert('RGB')
            if im.size not in ((280,242),(560,242)):
                raise ValueError(f'unexpected pageflip display: {im.size}')
            colors=len(im.getcolors(200000) or [])
            min_colors=min(min_colors,colors)
            if colors<5:raise ValueError(f'blank pageflip image at frame {i+1}: {colors} colors')
            x0,x1=(12,268) if im.width==280 else (24,536)
            pixels=im.crop((x0,16,x1,240)).tobytes()
            digest=hashlib.sha256(pixels).digest()
            # Ignore the border; compare the whole 256px BAT image.
            # Defective midpoint is a one-scanline floor-row copy.
            mid=im.crop((x0,124,x1,125)).tobytes()
            floor=im.crop((x0,234,x1,235)).tobytes()
            similarity=sum(a==b for a,b in zip(mid,floor))/len(mid)
            max_floor_copy=max(max_floor_copy,similarity)
            if similarity>=.90:raise ValueError(f'midpoint floor-row copy at frame {i+1}')
            n=int.from_bytes(bytes.fromhex(client.call('memread',hex(redraw_address),2,1)['hex']),'little')
            front=bytes.fromhex(client.call('memread',hex(front_address),1,1)['hex'])[0]
            if front>1:raise ValueError('invalid front page')
            if prev is not None:
                if n==prev_flip:
                    if front!=prev_front:raise ValueError('front page changed without flip counter')
                    if i-last_flip_frame>2:
                        frozen+=1
                        if digest!=prev:raise ValueError(f'visible page changed long after VBlank flip at frame {i+1}')
                else:
                    num_flips+=n-prev_flip
                    last_flip_frame=i
                    if front==prev_front and n-prev_flip==1:raise ValueError('page counter advanced but selection did not flip')
                if digest!=prev:changes+=1
            prev,prev_flip,prev_front=digest,n,front
    finally:client.close()
    if num_flips<3:raise ValueError(f'too few full VBlank page flips: {num_flips}')
    if changes<3:raise ValueError('camera input did not produce distinct page images')
    result={'passed':True,'frames':frames,'warmup':warmup,'complete_vblank_flips':num_flips,
            'new_visible_frames':changes,'unchanged_between_flips':frozen,
            'min_colors':min_colors,'max_midpoint_floor_byte_similarity':round(max_floor_copy,4),
            'note':'Only emulator validated; 2-color tile quantization is not pixel-equivalent to original 16-color renderer'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--elf',required=True)
    p.add_argument('--output',required=True);p.add_argument('--frames',type=int,default=540)
    a=p.parse_args()
    try:run(a.rom,a.elf,a.output,a.frames)
    except (ValueError,OSError,RuntimeError) as e:p.error(str(e))
