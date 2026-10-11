#!/usr/bin/env python3
"""Compare two independently compiled PCE height converters, not VCS FPS."""
import argparse
import json
from pathlib import Path


def compare(baseline, span, visual):
    if not visual.get('matched') or visual.get('differing_pixels') != 0:
        raise ValueError('VCS-span compositor has nonidentical emulator pixels')
    a = baseline['totals']
    b = span['totals']
    if not (a['passed'] and b['passed']):
        raise ValueError('benchmark did not pass')
    for key in ('video_frames', 'vram_words', 'changed_views'):
        if a[key] != b[key]:
            raise ValueError(f'changed {key}: {a[key]} versus {b[key]}')
    if a['turning_views_per_second'] != b['turning_views_per_second']:
        raise ValueError('turning dirty-view throughput changed')
    return {'passed': True, 'baseline': a, 'vcs_span': b,
            'pixel_count':visual['pixel_count'],
            'different_pixels':visual['differing_pixels'],
            'claim':'equivalent full-detail PCE image; per-routine profiler needed for compositor CPU ticks, no FPS gain claimed'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--span',type=Path,required=True)
    p.add_argument('--visual',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        report=compare(*(json.loads(p.read_text()) for p in (a.baseline,a.span,a.visual)))
    except (OSError,KeyError,ValueError) as e:
        p.error(str(e))
    a.output.parent.mkdir(exist_ok=True,parents=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
