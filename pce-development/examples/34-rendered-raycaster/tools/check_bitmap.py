#!/usr/bin/env python3
"""Independent screen-shape check for the 512x224 BAT-backed raycaster.

Input is an actual emulator PNG captured by `make run`; verifies separate
textured wall, ceiling, floor and no cyan palette holes. Never trusts G2TR
for pixel evidence. This checks screen content, not exact gameplay physics.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from PIL import Image


def check(path):
    im=Image.open(path).convert('RGB')
    if im.size!=(560,242):
        raise ValueError(f'expected emulator capture 560x242, got {im.size}')
    regions={
        'ceiling':(40,22,520,87),
        'walls':(60,90,500,152),
        'floor':(40,172,520,221),
    }
    counts={key:Counter(im.crop(box).get_flattened_data()) for key,box in regions.items()}
    all_pixels=Counter(im.get_flattened_data())
    if len(all_pixels)<9:
        raise ValueError(f'not enough pixel colours for textured bitmap: {len(all_pixels)}')
    for key,minimum in [('ceiling',3),('walls',5),('floor',3)]:
        if len(counts[key])<minimum:
            raise ValueError(f'{key}: expected >= {minimum} colours, got {len(counts[key])}')
    if max((n for (r,g,b),n in counts['walls'].items() if r>g and r>b),default=0)<1000:
        raise ValueError('missing textured warm wall surface')
    if sum(n for (r,g,b),n in counts['floor'].items() if r>g and g>=b)<2000:
        raise ValueError('missing checkerboard earth floor')
    if any(r<60 and g>120 and b>120 for r,g,b in all_pixels):
        raise ValueError('cyan pixel holes detected')
    return {'passed':True,'resolution':list(im.size),
            'colors':len(all_pixels),
            'region_colors':{k:len(v) for k,v in counts.items()},
            'evidence':'emulator screenshot; NOT game-authored telemetry'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screenshot',type=Path)
    args=parser.parse_args()
    try: result=check(args.screenshot)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
