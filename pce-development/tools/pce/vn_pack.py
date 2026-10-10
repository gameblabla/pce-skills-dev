#!/usr/bin/env python3
"""Offline visual-novel asset converter: one static BG, 2 mouth sprite frames.

Standalone Pillow-only converter. Generates deduplicated 4bpp background tiles,
32x32 BAT, VCE palettes, 16x16/4bpp sprite patterns, preview and VRAM audit.
For 16 *background* palettes on photographic assets, also see picture.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COLORS={'navy':(20,28,61),'blue':(36,65,102),'sky':(68,111,149),'glow':(128,174,181),
        'wall':(47,53,76),'shadow':(27,34,52),'hair':(25,37,58),'hair2':(42,50,73),
        'skin':(222,162,125),'skin2':(189,118,99),'eyes':(234,223,198),
        'jacket':(53,77,95),'jacket2':(77,120,131),'ink':(20,24,38),'white':(238,223,186)}

def demo(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    a=Image.new('RGB',(256,224),COLORS['navy']);d=ImageDraw.Draw(a)
    # Large, coherent static location: observation room at night, blue window.
    for y in range(12,153):
        col=COLORS['navy'] if y<42 else COLORS['blue'] if y<81 else COLORS['sky'] if y<123 else COLORS['glow']
        d.line((15,y,244,y),fill=col)
    for x in (16,73,132,190,244):d.rectangle((x,11,x+4,157),fill=COLORS['wall'])
    d.rectangle((15,11,245,16),fill=COLORS['shadow'])
    d.polygon([(15,139),(50,110),(78,135),(116,101),(161,145),(201,107),(244,133),(244,157),(15,157)], fill=COLORS['shadow'])
    for x,y in ((30,127),(62,143),(157,138),(215,130)):
        d.rectangle((x,y,x+7,y+2),fill=COLORS['glow'])
    d.rectangle((0,157,255,224),fill=COLORS['wall'])
    # Bust with readable silhouette (no external copyrighted character).
    d.ellipse((39,126,158,227),fill=COLORS['jacket'])
    d.polygon([(49,174),(84,142),(103,172),(116,145),(157,174),(149,223),(47,223)], fill=COLORS['jacket2'])
    d.rectangle((91,134,114,166),fill=COLORS['skin2'])
    d.ellipse((55,37,150,152),fill=COLORS['hair'])
    d.ellipse((70,52,139,151),fill=COLORS['skin2'])
    d.ellipse((71,53,133,145),fill=COLORS['skin'])
    d.polygon([(57,95),(57,53),(77,39),(111,37),(147,61),(136,84),(124,68),(102,70),(85,86),(71,78)], fill=COLORS['hair'])
    d.polygon([(72,62),(102,43),(132,52),(116,59),(99,67),(82,76)],fill=COLORS['hair2'])
    d.rectangle((88,94,95,97),fill=COLORS['ink']);d.rectangle((119,94,126,97),fill=COLORS['ink'])
    d.line((106,100,103,113,108,115),fill=COLORS['skin2'],width=2)
    # Mouth is its own sprite and stays OUT of the static picture.
    # Stylized bordered conversation panel at bottom.
    d.rectangle((6,172,250,220),fill=COLORS['ink'],outline=COLORS['glow'],width=2)
    d.rectangle((164,168,246,181),fill=COLORS['blue'],outline=COLORS['glow'])
    f=ImageFont.load_default()
    d.text((172,170),'NOVA',font=f,fill=COLORS['white'])
    d.text((164,187),'THE GATE OPENS',font=f,fill=COLORS['white'])
    d.text((164,199),'AT DAWN.',font=f,fill=COLORS['white'])
    a.save(out/'background.png')
    for opened,name in ((False,'mouth_closed.png'),(True,'mouth_open.png')):
        mouth=Image.new('RGBA',(16,16),(0,0,0,0));m=ImageDraw.Draw(mouth)
        # Opaque skin patch masks the static face where the mouth changes.
        m.ellipse((1,0,14,15),fill=(*COLORS['skin'],255))
        if opened:
            m.ellipse((4,4,12,12),fill=(*COLORS['ink'],255))
            m.rectangle((6,10,10,11),fill=(*COLORS['skin2'],255))
        else:
            m.line((4,8,12,8),fill=(*COLORS['ink'],255),width=2)
        mouth.save(out/name)
    return out


def vce(rgb):
    r,g,b=rgb
    return (round(r*7/255)<<3)|(round(g*7/255)<<6)|round(b*7/255)


def plane(pixels,w,h):
    """PCE 4bpp BG 8x8 or sprite 16x16 (plane-major for sprites)."""
    if (w,h)==(8,8):
        a=bytearray(32)
        for y in range(8):
            for x in range(8):
                n=pixels[y][x]
                for pl in range(4):
                    if n>>pl&1:a[16*(pl//2)+y*2+pl%2] |= 1<<(7-x)
        return bytes(a)
    if (w,h)==(16,16):
        a=bytearray(128)
        for y in range(16):
            for x in range(16):
                n=pixels[y][x]
                for pl in range(4):
                    if n>>pl&1:a[pl*32+y*2+x//8]|=1<<(7-x%8)
        return bytes(a)
    raise ValueError('tile dimensions must be 8x8 or 16x16')


def carray(name,data):
    lines=['const unsigned char '+name+'['+str(len(data))+'] = {']
    for i in range(0,len(data),24):lines.append('  '+','.join('0x%02x'%x for x in data[i:i+24])+',')
    return '\n'.join(lines+['};',''])


def pack(background,closed,opened,out,palette_mode="single"):
    background,closed,opened,out=map(Path,(background,closed,opened,out))
    with Image.open(background) as source:
        if source.size!=(256,224):
            raise ValueError('static scene must be exactly 256x224')
    frames=[Image.open(p).convert('RGBA') for p in (closed,opened)]
    if any(i.size!=(16,16) for i in frames):
        raise ValueError('mouth overlays must each be exactly 16x16 pixels')
    im=Image.open(background).convert('RGB')
    # One deterministic shared 16-color BG palette, no transparency in background.
    quant=im.quantize(colors=16,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    rgbpal=quant.getpalette()
    palette=[tuple(rgbpal[i*3:i*3+3]) for i in range(16)]
    indices=quant.load()
    pattern_map={}; patterns=[]; bat=[]
    for ty in range(28):
        for tx in range(32):
            px=[[indices[tx*8+x,ty*8+y] for x in range(8)] for y in range(8)]
            tile=plane(px,8,8)
            if tile not in pattern_map:
                pattern_map[tile]=len(patterns);patterns.append(tile)
            bat.append(0x0080+pattern_map[tile])
    if len(patterns)>512 and palette_mode=="single":
        raise ValueError('too many unique background patterns (>512): simplify art or use multi-bank streaming')
    bg=bytes().join(patterns)
    bgpal=b''.join(vce(rgb).to_bytes(2,'little') for rgb in palette)
    batting=b''.join(n.to_bytes(2,'little') for n in bat)
    palette_count=1
    if palette_mode=='multi':
        out.mkdir(parents=True,exist_ok=True)
        # The existing proven per-tile fitter supports all 16 BG palettes.
        # It needs Pillow + numpy, and picture.py/palfit.py/formats.py.
        try:
            from picture import convert
        except ImportError as exc:
            raise ValueError('multi mode needs picture.py, palfit.py, formats.py and numpy beside vn_pack.py') from exc
        manifest=convert(background,out/'multi_bg',(256,224),0x0800,32)
        bg=(out/'multi_bg.patterns.bin').read_bytes()
        bgpal=(out/'multi_bg.palettes.bin').read_bytes()
        batting=(out/'multi_bg.bat.bin').read_bytes()
        if len(bg)>512*32:
            raise ValueError('multi-palette picture has >512 patterns: lower artwork complexity or stream banks')
        palette_count=16
    # Sprite palette shared between both frames; transparent index zero.
    colors=[]
    for frame in frames:
        for r,g,b,a in frame.get_flattened_data():
            if a<128:continue
            c=(r,g,b)
            if c not in colors:colors.append(c)
    if len(colors)>15:
        raise ValueError('mouth frames use >15 distinct opaque colors; reduce overlay palette')
    spals=[(0,0,0)]+colors+[(0,0,0)]*(15-len(colors))
    sbytes=[]
    for frame in frames:
        data=list(frame.get_flattened_data())
        px=[[0 if data[y*16+x][3]<128 else colors.index(data[y*16+x][:3])+1
             for x in range(16)] for y in range(16)]
        sbytes.append(plane(px,16,16))
    vpal=bgpal
    spal=b''.join(vce(rgb).to_bytes(2,'little') for rgb in spals)
    sprite_data=b''.join(sbytes)
    if 0x0800+len(bg)//2>0x6000 or 0x6000+len(sprite_data)//2>0x7f00:
        raise ValueError('VRAM layout overlaps sprite region or SAT')
    out.mkdir(parents=True,exist_ok=True)
    h='''#ifndef VN_ASSETS_H\n#define VN_ASSETS_H\n#define VN_BG_WORD 0x0800u\n#define VN_BG_PALETTES %d\n#define VN_SPRITE_WORD 0x6000u\n#define VN_SAT_WORD 0x7f00u\n#define VN_MOUTH_X 98\n#define VN_MOUTH_Y 120\nextern const unsigned char vn_patterns[%d];\nextern const unsigned char vn_bat[%d];\nextern const unsigned char vn_bg_palette[%d];\nextern const unsigned char vn_sprite_palette[%d];\nextern const unsigned char vn_mouth_patterns[%d];\n#endif\n'''%(palette_count,len(bg),len(batting),len(vpal),len(spal),len(sprite_data))
    (out/'vn_assets.h').write_text(h)
    (out/'vn_assets.c').write_text('#include "vn_assets.h"\n'+''.join(carray(n,v) for n,v in
        [('vn_patterns',bg),('vn_bat',batting),('vn_bg_palette',vpal),('vn_sprite_palette',spal),('vn_mouth_patterns',sprite_data)]))
    if palette_mode=='single':
        decoded=Image.new('RGB',(256,224));d=decoded.load()
        for y in range(224):
            for x in range(256):d[x,y]=palette[indices[x,y]]
    else:
        decoded=Image.open(out/'multi_bg.preview.png').convert('RGB')
    for ix,frame in enumerate(frames):
        preview=decoded.convert('RGBA');preview.alpha_composite(frame,(98,120));preview.save(out/('preview_open.png' if ix else 'preview_closed.png'))
    manifest={'format':'pce-vn-pack-v1','canvas':[256,224],
              'background_unique_tiles':len(bg)//32,'background_raw_tiles':896,
              'background_dedup_ratio':round(1-(len(bg)//32)/896,4),
              'background_palette_count':palette_count, 'palette_mode':palette_mode,
              'bg_palette_entries':16*palette_count,'sprite_palette_entries':16,
              'mouth_changed_pixels':sum(a!=b for a,b in zip(frames[0].get_flattened_data(),frames[1].get_flattened_data())),
              'sprite_frames':2,'mouth_sprite_size':[16,16],
              'vram_words':{'bat':[0,1024],'background_patterns':[0x0800,0x0800+len(bg)//2],
                            'sprite_patterns':[0x6000,0x6000+len(sprite_data)//2],'sat':[0x7f00,0x7f00+256]},
              'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (background,closed,opened)},
              'generated_c_sha256':hashlib.sha256((out/'vn_assets.c').read_bytes()).hexdigest()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('demo',help='create reproducible coherent VN source PNGs')
    a.add_argument('--out',type=Path,required=True)
    b=sub.add_parser('pack',help='generate C assets, preview and memory accounting')
    for flag in ('background','closed','open','out'):
        b.add_argument('--'+flag,required=True,type=Path)
    b.add_argument('--palette-mode',choices=['single','multi'],default='single',
                   help='multi uses per-tile fitting with up to 16 BG palettes (requires numpy)')
    args=p.parse_args()
    try:
        if args.command=='demo':
            demo(args.out);print('Generated static picture and two mouth overlay PNGs in',args.out)
        else:print(json.dumps(pack(args.background,args.closed,args.open,args.out,args.palette_mode),indent=2))
    except (ValueError,OSError) as e:p.error(str(e))

if __name__=='__main__':main()
