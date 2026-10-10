#!/usr/bin/env python3
"""Build an original 16-colour top-down road BAT from offline drawing primitives.

This is a *scene handoff* demo, not a fake Mode7 raster renderer. For the
512x224 paired-BAT bitmap floor use examples/micro/86-mode7-bitmap-floor.
"""
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def planar_tile(pix):
    out=bytearray()
    for planes in ((0,1),(2,3)):
        for y in range(8):
            for plane in planes:
                byte=sum(((pix[y][x]>>plane)&1)<<(7-x) for x in range(8))
                out.append(byte)
    return bytes(out)

def render():
    im=Image.new('P',(512,256),8)
    d=ImageDraw.Draw(im)
    # Perspective road: intended for the mode-switch demo only.
    d.rectangle((0,0,511,31), fill=8)
    d.rectangle((0,32,511,89), fill=5)
    d.rectangle((0,90,511,110), fill=9)
    d.rectangle((0,111,511,255), fill=6)
    for y in range(112,256):
        half=18+((y-112)*110//144)
        center=128
        for xo in (0,256):
            d.rectangle((center-half+xo,y,center+half+xo,y),fill=8)
            d.line((center-half-3+xo,y,center-half+xo,y),fill=2 if (y//10)&1 else 1)
            d.line((center+half+xo,y,center+half+3+xo,y),fill=2 if (y//10)&1 else 1)
            if (y//18)&1:
                line_width=max(1,(y-104)//28)
                d.rectangle((center-line_width+xo,y,center+line_width+xo,y),fill=4)
    for x in range(0,512,64):
        d.rectangle((x+8,69,x+39,74),fill=1)
        d.polygon(((x,110),(x+32,75),(x+64,110)),fill=10)
    # Reuse the existing scene palette; solid shapes are already limited to 0..15.
    src=im.load(); ids={bytes(32):0};patterns=[bytes(32)];bat=[]
    for y in range(0,256,8):
        for x in range(0,512,8):
            tile=planar_tile([[src[x+dx,y+dy] for dx in range(8)] for dy in range(8)])
            if tile not in ids:
                ids[tile]=len(patterns);patterns.append(tile)
            bat.append(0x0080+ids[tile])
    if 0x0800+len(patterns)*16>=0x5000:raise ValueError('too many unique tiles')
    return im, b''.join(patterns), bat

def array(name, values, typ):
    fmt=lambda a:f'0x{a:04x}' if typ=='uint16_t' else f'0x{a:02x}'
    return f'static const {typ} {name}[{len(values)}] = {{\n'+''.join('    '+','.join(fmt(n) for n in values[i:i+16])+',\n' for i in range(0,len(values),16))+'};\n'

if __name__=='__main__':
    im,patterns,bat=render()
    header='#pragma once\n#include <stdint.h>\n/* Offline generated racing scene: no third-party artwork. */\n'
    header+=array('pce_race_patterns',patterns,'uint8_t')
    header+=array('pce_race_bat',bat,'uint16_t')
    (ROOT/'assets/race_assets.h').write_text(header)
    im.crop((0,0,256,224)).save(ROOT/'assets/race_preview.png')
    print(f'{len(patterns)//32} tiles; {len(bat)} BAT entries')
