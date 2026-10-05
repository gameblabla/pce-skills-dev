#!/usr/bin/env python3
"""Generate original indexed example art and the exact PCE tiles used by each ROM.

Requires Pillow and NumPy (the same dependencies as tools/pce converters).
No game assets, downloaded fonts, SVG renderer, or BIOS are required.
"""
from pathlib import Path
import sys
import math
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT.parent / 'tools/pce'))
from formats import planar_tile, planar_sprite

# Exact 9-bit VCE colors: index zero is the shared backdrop / sprite transparency.
COLORS = [(0,0,0),(7,7,7),(7,2,1),(1,6,7),(7,6,1),(2,2,7),(1,7,2),(7,1,5),
          (1,1,2),(2,3,4),(2,5,7),(4,7,2),(5,2,7),(7,7,3),(3,6,6),(7,3,4)]
FONT = ImageFont.load_default()
TITLES = ['PROJECT TEMPLATE','HELLO CD-ROM2','STATIC BACKGROUND','CD TO ARCADE RAM',
          'ARCADE RAM TO VRAM','SOUND AND MUSIC','SPRITES AND SAT','STAGED ANIMATION',
          'PLATFORMER','RASTER ROAD','SCROLLING SHOOTER','SCREEN SPACE HUD',
          'BANK RELOCATION','HEADLESS DEBUGGING','PYTHON MATH','VIDEO MODES',
          'PICTURE CONVERSION','BACKGROUND STREAMING','PLAYER COLLISION',
          'ENEMIES AND SHOTS','PALETTE FADES','BITMAP FONT','RASTER PARALLAX',
          'MEMORY MANAGEMENT','ADPCM AND PSG DDA']
WIDTHS = {0:256,8:256,9:512,10:256,17:256,18:256,19:256,22:512}


def image(size, color=8):
    im = Image.new('P', size, color)
    im.putpalette([v * 255 // 7 for rgb in COLORS for v in rgb] + [0] * (768 - 48))
    return im


def text(d, xy, value, color=1):
    # The built-in bitmap font keeps generation portable and colors exact.
    d.text(xy, value, font=FONT, fill=color)


def panel(d, box, label, color=3):
    d.rectangle(box, fill=9, outline=color, width=2)
    text(d, (box[0]+8, box[1]+8), label)


def landscape(im, collision=False):
    d = ImageDraw.Draw(im)
    d.rectangle((0,32,511,175), fill=5)
    d.ellipse((260,45,290,75), fill=4)
    for x in range(0,512,64):
        d.rectangle((x+8,56,x+39,63), fill=1)
        d.rectangle((x+16,48,x+31,55), fill=1)
        d.polygon([(x,144),(x+32,80),(x+64,144)], fill=10)
        d.polygon([(x+16,160),(x+48,104),(x+80,160)], fill=9)
    d.rectangle((0,176,511,255), fill=9)
    d.rectangle((0,176,511,183), fill=6)
    for y in range(184,256,16):
        for x in range(0,512,32):
            dx = 16 if (y//16)&1 else 0
            d.rectangle((x+dx,y,x+dx+30,y+14), outline=8)
    if collision:
        d.rectangle((192,64,199,175), fill=2)
        for y in range(64,176,8):
            d.line((192,y,199,y+7), fill=4)
    else:
        for x,y in [(104,144),(208,120),(352,144)]:
            d.rectangle((x,y,x+47,y+7), fill=6)
            d.rectangle((x,y+8,x+47,y+15), fill=9)


def scene(n):
    w = WIDTHS.get(n,320)
    im = image((512,256))
    d = ImageDraw.Draw(im)
    if n in (2,4,8,11,16,17,18,20):
        landscape(im, n == 18)
        if n == 11:
            text(d,(32,40),'LIVES 03   HEALTH',4)
            d.rectangle((144,40,204,47), fill=6)
        if n == 18:
            text(d,(144,48),'WALL',4)
    elif n in (10,19):
        for k in range(100):
            x,y = (k*73+17)%512, (k*47+43)%256
            d.point((x,y), fill=1 if k%3 else 10)
        for x,y in [(40,64),(200,128),(360,80)]:
            d.ellipse((x,y,x+24,y+24), fill=9, outline=10)
    elif n == 9:
        d.rectangle((0,32,511,255),fill=6)
        d.polygon([(220,32),(292,32),(432,255),(80,255)],fill=9)
        d.line((220,32,80,255),fill=1,width=3)
        d.line((292,32,432,255),fill=1,width=3)
        for y in range(48,256,32):
            d.rectangle((252,y,259,y+15),fill=4)
    elif n == 22:
        d.rectangle((0,32,511,63),fill=5)
        d.rectangle((0,64,511,127),fill=10)
        d.rectangle((0,128,511,191),fill=9)
        d.rectangle((0,192,511,255),fill=6)
        for x in range(0,512,64):
            d.rectangle((x+8,48,x+39,55),fill=1)
            d.polygon([(x,127),(x+32,72),(x+64,127)],fill=5)
            d.rectangle((x+16,144,x+47,191),fill=8)
            d.rectangle((x+20,152,x+27,159),fill=4)
            d.rectangle((x+36,168,x+43,175),fill=4)
            d.rectangle((x,208,x+47,215),fill=11)
    else:
        if n in (0,1,15,16):
            panel(d,(16,56,w-17,168),'LLVM-MOS / PC ENGINE')
            text(d,(32,88),'HELLO WORLD' if n==1 else 'DISPLAY READY',4)
            text(d,(32,112),'8x8 TILES + 9-BIT COLOR')
            for i in range(16):
                d.rectangle((24+i*16,144,37+i*16,159),fill=i)
        elif n in (3,12,23):
            labels = {3:['CD SECTOR','CPU STAGE','ARCADE RAM'],
                      12:['FIXED ROM','MPR3 MAP','BANKED CODE'],
                      23:['CPU RAM','VRAM','ARCADE RAM']}[n]
            for i,label in enumerate(labels):
                y=56+i*44
                panel(d,(24,y,w-25,y+32),label, [3,4,6][i])
                d.rectangle((w-100,y+12,w-36,y+21),fill=[3,4,6][i])
            text(d,(24,196),'NO DISC IN HUCARD MODE' if n==3 else 'EXPLICIT OWNERSHIP',4)
        elif n in (5,24):
            panel(d,(16,48,w-17,168),'WAVEFORM / SAMPLE PATH')
            points=[(x,108+int(22*math.sin(x*math.pi/32))) for x in range(24,w-24)]
            d.line(points,fill=3,width=2)
            text(d,(32,148),'PSG CHANNEL 4 / DDA',4)
            text(d,(24,184),'I: PLAY    II: STOP' if n==24 else 'FRAME-PACED DAC DEMO')
        elif n == 6:
            panel(d,(16,48,w-17,168),'16x16 HARDWARE SPRITE')
            d.rectangle((140,92,164,116),outline=3)
            text(d,(32,136),'SAT SLOT 00 / FOREGROUND',4)
        elif n == 7:
            panel(d,(16,48,w-17,176),'NEXT POSE -> UNUSED PATTERNS')
            text(d,(32,144),'UPLOAD / PUBLISH / REUSE',4)
        elif n == 13:
            panel(d,(16,48,w-17,168),'EMULATOR CAPTURE')
            text(d,(32,80),'VBLANK COUNTER ACTIVE',4)
            text(d,(32,104),'PNG FROM THE BUILT ROM')
            d.rectangle((32,136,w-33,151),fill=3)
        elif n == 14:
            panel(d,(16,48,w-17,168),'HOST-DERIVED CONSTANTS')
            text(d,(32,80),'128 WORDS x 2 = 256 BYTES',4)
            text(d,(32,112),'VDC ADDRESSES ARE WORDS')
        elif n == 21:
            panel(d,(16,48,w-17,176),'CUSTOM BITMAP FONT')
            for i,s in enumerate(['ABCDEFGHIJKLMNOPQRSTUVWXYZ','0123456789 + - = /','PCE  FOUR BITPLANES','8 PIXELS PER CHARACTER']):
                text(d,(32,80+i*24),s,4 if i==2 else 1)
    if n == 15:
        panel(d,(336,56,495,168),'512-DOT VIEW',4)
        text(d,(352,96),'EXTRA COLUMNS',3)
        d.line((319,32,319,223),fill=2)
    d.rectangle((0,0,511,31), fill=8)
    d.line((0,31,511,31),fill=3)
    text(d,(8,8),f'{n:02d}  {TITLES[n]}',1)
    if n not in (9,22):
        text(d,(8,208), {8:'LEFT / RIGHT TO WALK',10:'I: FIRE',11:'I: MOVE HUD UP',
                        17:'STREAMING THE ENTERING EDGE',18:'D-PAD: MOVE / WALL AT X=192',
                        19:'I: FIRE AT ENEMY',20:'VCE PALETTE ANIMATION',
                        15:'I: SWITCH 320 / 512 DOTS'}.get(n,'PC ENGINE DEVELOPMENT'),4)
    return im


def sprites(n):
    sheet = image((16*12,16),0)
    d=ImageDraw.Draw(sheet)
    # Player: an original tiny spacesuit, or ship in the shooting examples.
    if n in (10,19):
        d.polygon([(8,0),(15,13),(10,11),(8,15),(6,11),(0,13)],fill=3)
        d.rectangle((7,5,9,9),fill=1)
    else:
        d.rectangle((4,1,11,7),fill=4)
        d.rectangle((6,3,11,5),fill=3)
        d.rectangle((3,8,12,12),fill=1)
        d.rectangle((4,13,6,15),fill=2)
        d.rectangle((9,13,11,15),fill=2)
    if n == 9:
        d.rectangle((0,0,15,15),fill=0)
        d.rectangle((3,0,12,15),fill=2)
        d.rectangle((4,3,11,6),fill=3)
        d.rectangle((4,10,11,12),fill=8)
        for x in (1,13):
            d.rectangle((x,3,x+1,6),fill=1)
            d.rectangle((x,11,x+1,14),fill=1)
    d.rectangle((16+6,2,16+9,13),fill=4)  # projectile
    d.polygon([(32,2),(47,2),(44,10),(40,14),(36,10)],fill=2)
    d.rectangle((37,5,42,7),fill=4)  # enemy
    d.polygon([(56,3),(60,0),(63,4),(63,8),(56,15),(49,8),(49,4),(52,0)],fill=2)
    # Two 32x32 robot poses, split into four 16x16 patterns each.
    frames=[]
    for pose in range(2):
        robot=image((32,32),0); r=ImageDraw.Draw(robot)
        r.rectangle((8,0,23,10),fill=3); r.rectangle((11,3,20,6),fill=4)
        r.rectangle((6,11,25,23),fill=1); r.rectangle((11,14,20,20),fill=2)
        r.rectangle((0,5 if pose else 14,5,21),fill=3)
        r.rectangle((26,14,31,29 if pose else 21),fill=3)
        r.rectangle((7,24,12,31),fill=5); r.rectangle((19,24,24,31),fill=5)
        for y in (0,16):
            for x in (0,16): frames.append(robot.crop((x,y,x+16,y+16)))
    for i,cell in enumerate(frames,4): sheet.paste(cell,(i*16,0))
    return sheet


def array(name, data, ctype='uint8_t'):
    items = [f'0x{int(v):04x}' if ctype=='uint16_t' else f'0x{int(v):02x}' for v in data]
    rows=['    '+','.join(items[i:i+16])+',' for i in range(0,len(items),16)]
    return f'static const {ctype} {name}[{len(items)}] = {{\n'+ '\n'.join(rows)+'\n};\n'


def bake(folder,n):
    im=scene(n); sheet=sprites(n)
    pixels=np.asarray(im)
    patterns=[bytes(32)]; ids={patterns[0]:0}; bat=[]
    for y in range(0,256,8):
        for x in range(0,512,8):
            tile=planar_tile(pixels[y:y+8,x:x+8])
            if tile not in ids: ids[tile]=len(patterns); patterns.append(tile)
            bat.append(0x80+ids[tile])
    pattern_bytes=b''.join(patterns)
    # Reserve the custom font at 0x5000, sprites at 0x6000, SAT at 0x7f00.
    assert 0x0800 + len(pattern_bytes)//2 <= 0x5000
    sprite_bytes=b''.join(planar_sprite(np.asarray(sheet)[:,x:x+16]) for x in range(0,sheet.width,16))
    palettes=[b | r<<3 | g<<6 for r,g,b in COLORS]
    header = '#pragma once\n#include <stdint.h>\n/* Generated by ../tools/generate_graphics.py; do not edit. */\n'
    header += array('pce_demo_palette',palettes,'uint16_t')
    header += array('pce_demo_patterns',pattern_bytes)
    header += array('pce_demo_bat',bat,'uint16_t')
    header += array('pce_demo_sprite_pattern',sprite_bytes)
    (folder/'assets/demo_assets.h').write_text(header)
    im.crop((0,0,WIDTHS.get(n,320),224)).save(folder/'assets/source.png')
    sheet.save(folder/'assets/sprite-sheet.png')
    print(f'{folder.name}: {len(patterns)} tiles, {len(pattern_bytes)} pattern bytes')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--example', type=int, choices=range(len(TITLES)))
    args = parser.parse_args()
    for folder in sorted(ROOT.glob('[0-9][0-9]-*')):
        n = int(folder.name[:2])
        if args.example is None or args.example == n: bake(folder,n)
