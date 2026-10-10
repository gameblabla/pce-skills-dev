#!/usr/bin/env python3
"""Offline, *unverified hardware* dual-VDC texture layer planner for SGX.

Quantize each 32x32 source wall to at most 30 colours split into VDC A's
15 opaque slots and VDC B's 15 overlay slots (index 0 transparent).
Both BAT layers would require their own 256-glyph paired-pixel bitmap,
VPC composition, palette selection and timing. This generator is an asset
conversion and proof of per-tile colour budgets, NOT an SGX rendering demo.
"""
import argparse,json
from collections import Counter
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/wolftextures256.png'
PREVIEW=ROOT/'assets/sgx_dual_preview.png'
HEADER=ROOT/'src/sgx_texture_planes.h'
REPORT=ROOT/'assets/sgx_dual_plan.json'

def vce(color):return tuple(round(c*7/255)*255//7 for c in color)
def generate():
    im=Image.open(SRC).convert('RGB')
    if im.size!=(224,32):raise ValueError('expected seven 32x32 textures')
    preview=Image.new('RGB',im.size)
    plane_a=[];plane_b=[];palettes_a=[];palettes_b=[];report=[]
    total_error=0;total_pixels=0
    for material in range(7):
        crop=im.crop((material*32,0,(material+1)*32,32))
        q=crop.quantize(colors=30,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB')
        counter=Counter(q.get_flattened_data())
        entries=[vce(rgb) for rgb,_ in counter.most_common()]
        # Hardware VCE is 3:3:3; de-duplicate colors AFTER quantization.
        entries=list(dict.fromkeys(entries))[:30]
        if not entries:raise ValueError('empty texture')
        # Stripe the palette entries across independent VDC planes so this
        # reference atlas actually exercises both layers, even when its
        # 3:3:3-quantized colours fit in a single 15-colour palette.
        base=entries[::2][:15];overlay=entries[1::2][:15]
        palettes_a.append(base);palettes_b.append(overlay)
        la=[];lb=[]
        for y in range(32):
            for x in range(0,32,2):
                va=[];vb=[]
                for xx in (x,x+1):
                    rgb=crop.getpixel((xx,y))
                    i=min(range(len(entries)),key=lambda k:sum((rgb[j]-entries[k][j])**2 for j in range(3)))
                    pix=entries[i];preview.putpixel((material*32+xx,y),pix)
                    total_error+=sum(abs(rgb[j]-pix[j]) for j in range(3));total_pixels+=3
                    if i&1:va.append(0);vb.append(i//2+1)
                    else:va.append(i//2+1);vb.append(0)
                la.append((va[0]<<4)|va[1]);lb.append((vb[0]<<4)|vb[1])
        plane_a.append(la);plane_b.append(lb)
        report.append({'material':material,'source_unique':len(set(crop.get_flattened_data())),
                       'vdc_a_colors':len(base),'vdc_b_colors':len(overlay),
                       'packed_pair_bytes_per_vdc':len(la)})
    lines=['/* Offline SGX 2x VDC asset plan; NOT a tested SGX runtime. */',
           '#ifndef SGX_TEXTURE_PLAN_H','#define SGX_TEXTURE_PLAN_H',
           'static const uint8_t sgx_texture_a[7][512]={']
    for pixels in plane_a:
        lines.append('  {');lines+=['    '+','.join('0x%02x'%b for b in pixels[i:i+16])+',' for i in range(0,512,16)];lines.append('  },')
    lines.append('};');lines.append('static const uint8_t sgx_texture_b[7][512]={')
    for pixels in plane_b:
        lines.append('  {');lines+=['    '+','.join('0x%02x'%b for b in pixels[i:i+16])+',' for i in range(0,512,16)];lines.append('  },')
    lines+=['};','#endif','']
    data={'kind':'offline dual-VDC per-material layered colour allocation',
          'runtime_implemented':False,'runtime_verified':False,
          'hardware_note':'Requires VPC overlay priorities and independent VDC bitmap/palette setup; preview is software composited.',
          'reference':'PCEdev PCE bitmap mode: SGX 128x128x241 theoretical palette limit (not arbitrary true RGB 256).',
          'source_unique_colours':len(set(im.get_flattened_data())),
          'dual_layer_vce_colour_mae':round(total_error/total_pixels,3),
          'vdc_a_palette_sets':7,'vdc_b_palette_sets':7,
          'per_material':report,
          'vdc_a_palettes_rgb':palettes_a,'vdc_b_palettes_rgb':palettes_b,
          'total_rom_plane_bytes':7*512*2}
    return '\n'.join(lines),json.dumps(data,indent=2)+'\n',preview

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    header,report,preview=generate()
    if a.check:
        if not HEADER.is_file() or HEADER.read_text()!=header:raise SystemExit('SGX plane header stale')
        if not REPORT.is_file() or REPORT.read_text()!=report:raise SystemExit('SGX plan stale')
        if not PREVIEW.is_file() or Image.open(PREVIEW).convert('RGB').tobytes()!=preview.tobytes():
            raise SystemExit('SGX software-composited preview stale')
    else:
        HEADER.write_text(header);REPORT.write_text(report);preview.save(PREVIEW)
    print(json.dumps({k:json.loads(report)[k] for k in ('runtime_verified','source_unique_colours','dual_layer_vce_colour_mae','total_rom_plane_bytes')}))
if __name__=='__main__':main()
