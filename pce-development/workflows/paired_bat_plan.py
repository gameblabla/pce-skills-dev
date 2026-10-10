#!/usr/bin/env python3
"""Offline source-of-truth for PCEdev's 512x224 paired-BAT pseudo-bitmap.

Full: 128x128 independent 4-bit pixels, no spare BAT page, progressive writes.
Atomic: 128x64 pixels, two independent 64x64 BAT half-pages, VBlank flip.
Neither is a planar framebuffer or a real 512x224 pixel-addressable display.
No network, emulator, compiler or target-side 32-bit arithmetic is needed.
"""
import argparse
import json
from pathlib import Path

BAT_WORDS=128*64
GLYPH_START_WORD=0x2000
GLYPH_WORDS=256*16
COLS=64


def word_address(y, pair, *, mode='full', page=0):
    if not isinstance(y,int) or not isinstance(pair,int) or not isinstance(page,int):
        raise ValueError('row, pair and page must be integers')
    if pair<0 or pair>=COLS:
        raise ValueError('BAT pair column must be 0..63')
    if mode=='full':
        if page!=0 or y<0 or y>=128:
            raise ValueError('full-resolution buffer has no second page')
        return ((y&63)<<7)+((y>>6)<<6)+pair
    if mode=='atomic':
        if page not in (0,1) or y<0 or y>=64:
            raise ValueError('atomic buffer has two pages of exactly 64 rows')
        return (y<<7)+(page<<6)+pair
    raise ValueError('mode must be full or atomic')


def plan(mode, *, batch_rows=8):
    if mode not in ('full','atomic'):
        raise ValueError('unknown paired-BAT mode')
    if batch_rows not in (4,8):
        raise ValueError('only measured 4-row and 8-row TIA batches are allowed')
    rows=128 if mode=='full' else 64
    pages=1 if mode=='full' else 2
    addresses=[]
    for page in range(pages):
        cur=[word_address(y,x,mode=mode,page=page) for y in range(rows) for x in range(COLS)]
        if len(set(cur))!=rows*COLS:
            raise ValueError('colliding BAT words within a page')
        addresses.append(set(cur))
    if pages==2 and addresses[0]&addresses[1]:
        raise ValueError('back page overlaps visible front page')
    if set.union(*addresses)!=set(range(BAT_WORDS)):
        raise ValueError('BAT layout does not cover its allocated 8192 words')
    if GLYPH_START_WORD<BAT_WORDS:
        raise ValueError('glyph patterns overlap BAT')
    # Exactly 223 raster events after VBlank. The source row starts at 0.
    physical_source=[]
    y=phase=0
    for _ in range(223):
        phase+=(4 if mode=='full' else 2)
        if phase>=7:
            phase-=7
            y+=1
        physical_source.append(y)
    if physical_source[-1]!=rows-1:
        raise ValueError('raster mapping does not end on last logical source row')
    return {
        'mode':mode,'video_pixels':[512,224],
        'logical_pixels':[128,rows], 'actual_colours_per_pixel':16,
        'paired_bitmaps':pages,'bat_words':BAT_WORDS,
        'words_per_page':rows*COLS,'bytes_per_page':rows*COLS*2,
        'glyph_start_word':GLYPH_START_WORD,'glyph_words':GLYPH_WORDS,
        'pair_glyphs':256,'tiles_per_scanline':COLS,
        'batch_rows':batch_rows,'tia_bytes_per_batch':batch_rows*COLS*2,
        'batches_per_complete_image':rows//batch_rows,
        'presentation':'vblank-atomic-bxr-swap' if mode=='atomic' else 'progressive-bat',
        'independent_pages':not bool(pages==1),
        'last_raster_source_row':physical_source[-1],
        'row_repeats_max':max(physical_source.count(i) for i in range(rows)),
        'reserved_other_vram_words':0x10000-(GLYPH_START_WORD+GLYPH_WORDS),
        'warnings':[
            '512x224 video is NOT 512x224 independently addressable pixels',
            'CPU writes to VDC BAT are not equivalent to a planar framebuffer',
            'Do not compare 128x64 atomic redraw counts with 128x128 full redraw counts as equal pixel work',
            'VBlank-only TIA transfer timings are emulator-validated, not hardware certified',
            'PCEdev alternative 5-bit/palette/dither scheme is theoretical here and is not implemented'
        ]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('full','atomic'),required=True)
    p.add_argument('--batch-rows',type=int,default=8)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        r=plan(a.mode,batch_rows=a.batch_rows)
    except ValueError as exc:
        p.error(str(exc))
    rendered=json.dumps(r,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(rendered)
    print(rendered,end='')
if __name__=='__main__':main()
