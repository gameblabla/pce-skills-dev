#!/usr/bin/env python3
"""Contrast progressive BAT commits with VRAM-backed complete-image copies.

A DMA-presented image is *not* an atomic BAT-base page flip on the PCE. Keep
wall-image equivalence independent of throughput and report costs honestly.
"""
import argparse
import json
from pathlib import Path


def compare(original, buffered, visual):
    if not visual.get('matched') or visual.get('differing_pixels') != 0:
        raise ValueError('settled bitmap is not exactly equivalent')
    if original['totals']['video_frames'] != buffered['totals']['video_frames']:
        raise ValueError('benchmark video-frame window differs')
    old=original['totals'];new=buffered['totals']
    return {
        'passed': True,
        'logical_resolution': [128,128],
        'standard_progressive_dirty_view_commits_per_second':old['turning_views_per_second'],
        'buffered_completed_dma_presentations_per_second':new['turning_views_per_second'],
        'standard_completed_passes':old['changed_views'],
        'buffered_completed_presentations':new['changed_views'],
        'standard_bat_words':old['vram_words'],
        'buffered_offscreen_bat_words':new['vram_words'],
        'buffered_additional_dma_words_per_present':8192,
        'buffered_total_dma_words':8192 * new['changed_views'],
        'buffered_dma_copies_per_present':2,
        'fully_settled_pixels_identical':True,
        'caveat':'Two VRAM DMA transfers can straddle display frames. This is an offscreen buffer, not a tear-free atomic page flip.',
        'hardware_validation':'not tested on physical PC Engine hardware',
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for flag in ('old','new','visual','output'):
        ap.add_argument('--'+flag,required=True)
    args=ap.parse_args()
    result=compare(json.loads(Path(args.old).read_text()),
                   json.loads(Path(args.new).read_text()),
                   json.loads(Path(args.visual).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError) as exc: raise SystemExit(f'VRAM buffer comparison failed: {exc}')
