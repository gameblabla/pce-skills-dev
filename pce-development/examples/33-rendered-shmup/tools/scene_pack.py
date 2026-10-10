#!/usr/bin/env python3
"""Offline single-palette PNG -> deduplicated PCE BG + 16x16 SAT sprite pack.

Unlike generated handwritten C arrays this validates the VRAM layout and sprite
palette before producing a single header/source pair and preview report.
Only Pillow is required, with no compiler, network, or BIOS at generation time.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

# Fixed indexed palette. Index 0 is transparent for sprites, but opaque for BG.
RGB = [
 (7,12,31), (21,33,62), (35,55,90), (52,80,117),
 (86,130,166), (148,198,218), (221,239,229), (250,241,179),
 (224,181,98), (185,104,76), (121,63,75), (71,48,73),
 (31,91,84), (56,139,109), (115,185,117), (231,93,109),
]

def vce(rgb):
    r,g,b=rgb
    return (round(r*7/255)<<3)|(round(g*7/255)<<6)|round(b*7/255)

def plane(pixels, width):
    if width==8:
        out=bytearray(32)
        for y in range(8):
            for x in range(8):
                n=pixels[y][x]
                for p in range(4):
                    if n&(1<<p):out[(p//2)*16+2*y+(p%2)] |= 1<<(7-x)
    elif width==16:
        out=bytearray(128)
        for y in range(16):
            for x in range(16):
                n=pixels[y][x]
                for p in range(4):
                    if n&(1<<p):out[p*32+y*2+(x//8)] |= 1<<(7-(x&7))
    else:raise ValueError('only 8x8 BG and 16x16 sprite supported')
    return bytes(out)

def demo(kind, folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(256,224),RGB[0]);d=ImageDraw.Draw(image)
    if kind=='shmup':
        for y in range(224):
            d.rectangle((0,y,255,y),fill=RGB[1+min(2,y//80)])
        for i in range(100):
            x=(i*73+19)%256;y=(i*97+31)%224
            d.point((x,y),fill=RGB[5 if i%5 else 7])
            if i%8==0:d.line((x-1,y,x+1,y),fill=RGB[4])
        for y in range(0,224,32):
            d.line((0,y,255,y),fill=RGB[2])
        d.rectangle((1,1,254,222),outline=RGB[3],width=1)
    elif kind=='racing':
        for y in range(224):
            if y<84:col=RGB[1+min(4,y//17)]
            else:col=RGB[13 if (y//16)%2 else 12]
            d.line((0,y,255,y),fill=col)
        for y in range(84,224):
            half=10+(y-84)*56//140
            l=128-half;r=128+half
            d.line((l,y,r,y),fill=RGB[2 if (y//16)%2 else 3])
            for side in (l,r):
                d.line((side-3,y,side+3,y),fill=RGB[6 if (y//10)%2 else 15])
            stripe=max(1,(y-84)//20)
            if (y//(12+stripe))%2==0:
                d.line((126,y,130,y),fill=RGB[7])
        d.line((0,83,255,83),fill=RGB[5],width=2)
    else:raise ValueError('genre must be shmup or racing')
    image.save(folder/'background.png')
    # Sprite atlas is 16x16 per frame, laid horizontally, no alpha for BG.
    atlas=Image.new('RGBA',(64,16),(0,0,0,0));ds=ImageDraw.Draw(atlas)
    if kind=='shmup':
        ds.polygon([(8,0),(1,14),(8,11),(15,14)],fill=RGB[5])
        ds.polygon([(8,2),(5,11),(11,11)],fill=RGB[7])
        ds.polygon([(16+8,1),(16+1,8),(16+8,15),(16+15,8)],fill=RGB[15]);ds.rectangle((22,6,26,10),fill=RGB[7])
        ds.rectangle((32+7,1,32+8,14),fill=RGB[7]);ds.rectangle((32+6,5,32+9,10),fill=RGB[8])
        ds.ellipse((49,2,62,14),fill=RGB[9]);ds.ellipse((53,5,58,10),fill=RGB[7])
    else:
        ds.polygon([(8,0),(1,13),(3,15),(13,15),(15,13)],fill=RGB[15]);ds.rectangle((4,6,12,10),fill=RGB[6]);ds.point((8,3),fill=RGB[7])
        ds.polygon([(16+8,1),(16+2,14),(16+14,14)],fill=RGB[8]);ds.rectangle((22,6,26,11),fill=RGB[6])
        ds.rectangle((34,1,46,14),fill=RGB[9]);ds.rectangle((36,3,44,10),fill=RGB[7]);ds.rectangle((36,12,44,13),fill=RGB[15])
        ds.ellipse((49,4,62,12),fill=RGB[6]);ds.rectangle((52,6,59,9),fill=RGB[15])
    atlas.save(folder/'sprites.png')
    return folder

def carray(name,content):
    lines=['const unsigned char '+name+'['+str(len(content))+'] = {']
    lines+=['  '+','.join(f'0x{b:02x}' for b in content[i:i+24])+',' for i in range(0,len(content),24)]
    return '\n'.join(lines+['};',''])

def pack(background,sprites,out):
    background,sprites,out=map(Path,(background,sprites,out))
    with Image.open(background) as im:
        if im.size!=(256,224):raise ValueError('background must be exactly 256x224')
        if im.mode not in ('RGB','RGBA'):raise ValueError('background must be RGB or RGBA')
        if im.mode=='RGBA' and any(p[3]!=255 for p in im.get_flattened_data()):raise ValueError('background must be fully opaque')
        colors=list(im.convert('RGB').getdata())
    palette_lookup={c:i for i,c in enumerate(RGB)}
    if any(c not in palette_lookup for c in colors):
        raise ValueError('background uses colors outside fixed 16-color palette; use demo palette or quantize offline')
    values=[palette_lookup[c] for c in colors]
    pattern_ids={};patterns=[];bat=[]
    for yy in range(28):
        for xx in range(32):
            px=[[values[(yy*8+y)*256+xx*8+x] for x in range(8)] for y in range(8)]
            blob=plane(px,8)
            if blob not in pattern_ids:
                pattern_ids[blob]=len(patterns);patterns.append(blob)
            bat.append(0x0080+pattern_ids[blob])
    if len(patterns)>512:raise ValueError('more than 512 unique tiles; simplify scene or stream assets')
    with Image.open(sprites) as im:
        if im.size!=(64,16):raise ValueError('sprite atlas must be 64x16 (4 x 16x16)')
        sprite=im.convert('RGBA'); pixels=list(sprite.get_flattened_data())
    # Reserve transparent colour at zero. Sprite colors share indexed palette 1..15.
    sp=[]
    for frame in range(4):
        px=[]
        for y in range(16):
            row=[]
            for x in range(16):
                rgb= pixels[y*64+frame*16+x]
                if rgb[3]<128:n=0
                elif rgb[:3] not in palette_lookup:raise ValueError('sprite color outside fixed palette')
                else:
                    n=palette_lookup[rgb[:3]]
                    if n==0:raise ValueError('sprite uses reserved transparent index 0 as opaque')
                row.append(n)
            px.append(row)
        sp.append(plane(px,16))
    tiles=b''.join(patterns);bat_data=b''.join(t.to_bytes(2,'little') for t in bat)
    sprite_data=b''.join(sp)
    if 0x0800+len(tiles)//2>0x6000:raise ValueError('BG patterns overlap sprite VRAM at $6000')
    bg_palette=b''.join(vce(c).to_bytes(2,'little') for c in RGB)
    sprite_palette=bg_palette
    data=[('scene_patterns',tiles),('scene_bat',bat_data),('scene_bg_palette',bg_palette),('scene_sprite_palette',sprite_palette),('scene_sprites',sprite_data)]
    out.mkdir(parents=True,exist_ok=True)
    h=['#ifndef SCENE_ASSETS_H','#define SCENE_ASSETS_H','#define SCENE_BG_WORD 0x0800u','#define SCENE_SPRITE_WORD 0x6000u','#define SCENE_SAT_WORD 0x7f00u']
    h +=[f'extern const unsigned char {name}[{len(blob)}];' for name,blob in data]
    h+=['#endif','']
    (out/'scene_assets.h').write_text('\n'.join(h))
    (out/'scene_assets.c').write_text('#include "scene_assets.h"\n'+''.join(carray(n,v) for n,v in data))
    report={'format':'pce-scene-pack-v1','canvas':[256,224], 'source_tiles':896,
            'unique_tiles':len(patterns),'sprite_frames':4,'sprite_size':[16,16],
            'vram_word_ranges':{'bat':[0,1024], 'bg':[2048,2048+len(tiles)//2],
                                'sprites':[24576,24576+len(sprite_data)//2], 'sat':[32512,32768]},
            'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (background,sprites)}}
    (out/'scene_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('demo');a.add_argument('--genre',required=True,choices=['shmup','racing']);a.add_argument('--out',required=True,type=Path)
    a=sub.add_parser('pack');a.add_argument('--background',required=True,type=Path);a.add_argument('--sprites',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=demo(args.genre,args.out) if args.cmd=='demo' else pack(args.background,args.sprites,args.out)
        print(json.dumps(result,indent=2,default=str))
    except (ValueError,OSError) as exc:parser.error(str(exc))
if __name__=='__main__':main()
