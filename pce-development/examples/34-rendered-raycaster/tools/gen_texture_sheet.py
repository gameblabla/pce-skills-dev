#!/usr/bin/env python3
"""Convert 7x(32x32) Wolf textures for paired-BAT PCE.

PCE: sixteen VCE colours, 32x32 samples on nearby walls, 16x16 far,
light/dark variants from palette-only nearest colours, packed 2 pixel/BAT.
SuperGrafx: preserve 256-source-colour RGB reference plus an honest dual-VDC
*planning* manifest. 256 unique arbitrary colours are NOT guaranteed by
transparent VDC compositing; this tool does not claim a tested SGX ROM.
"""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
IN16=ROOT/'assets/wolftextures16.png'; IN256=ROOT/'assets/wolftextures256.png'
OUT=ROOT/'src/sheet_pairs.h'; PAL=ROOT/'src/sheet_palette.h'
MANIFEST=ROOT/'assets/texture_manifest.json'
HIRES=ROOT/'src/hires_texels.h'
# Slot zero is the VCE backdrop. Slots 1..15 cover every distinct colour
# of the supplied 16-colour sheet, in an order giving 4 sky and 3 floor slots.
BACKDROP=(0,0,64)
PREFERRED=((6,1,99),(0,0,159),(80,81,80),(46,44,39),
           (80,59,27),(122,82,41),(140,140,140),(179,180,180),
           (98,0,0),(175,13,0),(147,9,26),(77,1,81),
           (175,170,0),(123,124,124),(0,0,0))
PALETTE=(BACKDROP,)+PREFERRED
STYLE_COUNT=14; TEX_U=16; TEX_V=16

def distance(a,b):return sum((x-y)*(x-y) for x,y in zip(a,b))
def nearest(rgb):return min(range(1,16),key=lambda k:distance(rgb,PALETTE[k]))
def dark(index):
    rgb=PALETTE[index];dim=tuple(int(c*0.68) for c in rgb)
    return min(range(1,16),key=lambda k:distance(dim,PALETTE[k]))

def converted():
    im=Image.open(IN16).convert('RGB')
    if im.size!=(224,32): raise ValueError('PCE texture atlas must be 7 * 32 by 32')
    unique=set(im.get_flattened_data());assert unique==set(PREFERRED),f'unexpected sheet colours: {len(unique)}'
    # Explicit nearest-neighbour 2:1 sampling is reproducible, no Lanczos
    # blur adding non-palette colours or runtime texture scaling on 6280.
    walls=[]
    for material in range(7):
        tex=[[nearest(im.getpixel((material*32+u*2+1,v*2+1))) for u in range(16)] for v in range(16)]
        walls.append(tex)
    pairs=[]
    for material in range(7):
        for shade in range(2):
            pixels=walls[material]
            pairs.append([[((dark(pixels[v][u]) if shade else pixels[v][u])<<4) |
                (dark(pixels[v][(u+1)&15]) if shade else pixels[v][(u+1)&15])
                for v in range(16)] for u in range(16)])
    return pairs

def generate_hires():
    # Full 32x32 source, TWO 4-bit texels per ROM byte (vertical nibble pair).
    # 7 * 32 * 16 = 3,584 B: no larger than the prior 16x32 byte table.
    im=Image.open(IN16).convert('RGB')
    tex=[]
    for material in range(7):
        tex.append([[((nearest(im.getpixel((material*32+u,v*2)))<<4) |
                       nearest(im.getpixel((material*32+u,v*2+1))))
                     for v in range(16)] for u in range(32)])
    lines=['/* Generated: original 32x32 artwork, packed vertical 4-bit texels. */',
           '#ifndef PCE_RAY_HIRES_TEXELS_H','#define PCE_RAY_HIRES_TEXELS_H',
           'static const uint8_t ray_wall_hires[7][32][16] = {']
    for mat in tex:
        lines.append('    {')
        for col in mat:
            lines.append('        {'+','.join(f'0x{v:02x}' for v in col)+'},')
        lines.append('    },')
    lines+=['};','static const uint8_t ray_hires_dark[16] = {'+
            ','.join(str(dark(k)) for k in range(16))+'};','#endif','']
    return '\n'.join(lines)

def generate():
    pairs=converted()
    lines=['/* Generated from assets/wolftextures16.png, 7 materials x 2 shades. */',
           '#ifndef PCE_SHEET_PAIRS_H','#define PCE_SHEET_PAIRS_H',
           'static const uint8_t ray_sheet_pairs[14][16][16]={']
    for s in pairs:
        lines+=['    {']
        for row in s:lines.append('        {'+','.join(f'0x{a:02x}' for a in row)+'},')
        lines+=['    },']
    lines+=['};','#endif','']
    ps=['/* VCE 3:3:3 colours from supplied 15-colour source sheet. */',
        '#ifndef PCE_SHEET_PALETTE_H','#define PCE_SHEET_PALETTE_H',
        'static const uint16_t ray_sheet_palette[16]={']
    for r,g,b in PALETTE:
        ps.append(f'    VCE_COLOR({round(r*7/255)},{round(g*7/255)},{round(b*7/255)}),')
    ps+=['};',
         '/* PCEdev-inspired blend between two 4-bit paired-BAT colours. */',
         'static const uint8_t ray_palette_blend_packed[128]={']
    for a in range(16):
        values=[]
        for b in range(16):
            # Match the final 3:3:3 VCE colours, not source 24-bit colours.
            def q(c):return tuple(round(v*7/255) for v in c)
            qa,qb=q(PALETTE[a]),q(PALETTE[b])
            blend=tuple((qa[k]+qb[k])/2 for k in range(3))
            mid=min(range(16),key=lambda k:sum((q(PALETTE[k])[i]-blend[i])**2 for i in range(3)))
            values.append(mid)
        ps.append('    '+','.join(f'0x{(values[i]<<4)|values[i+1]:02x}' for i in range(0,16,2))+',')
    ps+=['};','#endif','']
    sg=Image.open(IN256).convert('RGB')
    if sg.size!=(224,32):raise ValueError('SGX texture atlas must be 7*32 by 32')
    unique256=len(set(sg.get_flattened_data()))
    manifest={'source_16_sha256':hashlib.sha256(IN16.read_bytes()).hexdigest(),
              'source_256_sha256':hashlib.sha256(IN256.read_bytes()).hexdigest(),
              'tile_count':7,'source_tile_px':[32,32],'pce_tile_px':[16,16],
              'near_wall_tile_px':[32,32],
              'near_wall_packed_bytes':7*32*16,
              'subpixel_blend_packed_bytes':128,
              'source_pce_unique_colours':len(set(Image.open(IN16).convert('RGB').get_flattened_data())),
              'pce_palette_slots':16,'pce_pair_variants':14*16,'pce_lookup_bytes':14*16*16,
              'sgx_source_unique_colours':unique256,
              'sgx_implementation':'RGB reference/art input only; requires separate two-VDC compositing implementation and visual validation',
              'sgx_limit':'SGX paired-BAT pseudo-bitmap is described as up to 241 colours, not arbitrary true 256-colour pixels',
              'no_sgx_runtime_claim':True}
    return '\n'.join(lines),'\n'.join(ps),json.dumps(manifest,indent=2)+'\n'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
    for path,data in zip((OUT,PAL,MANIFEST,HIRES),(*generate(),generate_hires())):
        if a.check:
            if not path.is_file() or path.read_text()!=data:ap.error(f'{path} stale')
        else:path.write_text(data)
    print('PCE 7 materials, 14 shade styles, 16 U, 16 V; 32x32 packed near textures; SGX reference verified')
if __name__=='__main__':main()
