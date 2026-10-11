#!/usr/bin/env python3
"""Offline source-of-truth for PCEdev's 512x224 paired-BAT pseudo-bitmap.

Only the 128x128 logical pixel view is supported; there is no spare BAT page.
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
    if mode!='full' or page!=0:
        raise ValueError('only the 128x128 progressive layout is supported')
    if not isinstance(y,int) or not isinstance(pair,int):
        raise ValueError('row and pair must be integers')
    if not 0 <= y < 128 or not 0 <= pair < COLS:
        raise ValueError('row must be 0..127, pair must be 0..63')
    # Mirror the actual midpoint-seam fix in gen_sparse_irq.bat_row():
    # logical y=64 occupies physical row 63 of the second BAT half.
    row=((y-1)&63) if y>=64 else y
    return (row<<7)+((y>>6)<<6)+pair


def plan(mode, *, batch_rows=8):
    if mode!='full':
        raise ValueError('only full (128x128) is supported')
    if batch_rows not in (4,8):
        raise ValueError('only measured 4-row and 8-row batches are allowed')
    addresses={word_address(y,p) for y in range(128) for p in range(COLS)}
    if addresses!=set(range(BAT_WORDS)):
        raise ValueError('paired BAT does not cover all 8192 words exactly once')
    if GLYPH_START_WORD<BAT_WORDS:
        raise ValueError('fixed glyph patterns overlap BAT')
    physical_source=[]
    y=phase=0
    for _ in range(223):
        phase+=4
        if phase>=7:
            phase-=7
            y+=1
        physical_source.append(y)
    if physical_source[-1]!=127:
        raise ValueError('raster mapping does not end on last logical source row')
    return {'mode':'full','video_pixels':[512,224],
            'logical_pixels':[128,128],'actual_colours_per_pixel':16,
            'paired_bitmaps':1,'bat_words':BAT_WORDS,'words_per_page':BAT_WORDS,
            'bytes_per_page':BAT_WORDS*2,'glyph_start_word':GLYPH_START_WORD,
            'glyph_words':GLYPH_WORDS,'pair_glyphs':256,'tiles_per_scanline':COLS,
            'batch_rows':batch_rows,'tia_bytes_per_batch':batch_rows*COLS*2,
            'batches_per_complete_image':128//batch_rows,
            'presentation':'progressive-bat','independent_pages':False,
            'midpoint_row64_physical_row':63,
            'last_raster_source_row':physical_source[-1],
            'row_repeats_max':max(physical_source.count(i) for i in range(128)),
            'reserved_other_vram_words':0x10000-(GLYPH_START_WORD+GLYPH_WORDS),
            'warnings':['Example implementation. Not speed optimized, has issues.',
                        'This is a progressively updated BAT, not atomic presentation',
                        'CPU writes to VDC BAT are not planar framebuffer writes',
                        'Emulator raster timing is not hardware-certified']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('full',),required=True)
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
