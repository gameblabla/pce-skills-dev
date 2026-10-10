#!/usr/bin/env python3
"""Assert that two real emulator captures differ ONLY inside the mouth sprite.
Do not substitute the offline asset preview for a real emulator capture.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

def check(closed,opened,*,x=98,y=120):
    with Image.open(closed) as img:a=img.convert('RGB')
    with Image.open(opened) as img:b=img.convert('RGB')
    if a.size!=b.size or a.width<256 or a.height<224:
        raise ValueError('expected matching emulator captures containing the 256x224 scene')
    left=(a.width-256)//2; top=(a.height-224)//2
    expected=(left+x,top+y,left+x+16,top+y+16)
    bounds=ImageChops.difference(a,b).getbbox()
    if not bounds:
        raise ValueError('mouth animation not visible: captures are identical')
    if not (expected[0]<=bounds[0]<bounds[2]<=expected[2] and
            expected[1]<=bounds[1]<bounds[3]<=expected[3]):
        raise ValueError(f'frame difference escaped mouth sprite: {bounds}, expected within {expected}')
    diff=ImageChops.difference(a,b)
    n=sum(1 for r,g,b in diff.get_flattened_data() if r or g or b)
    if n<12:
        raise ValueError(f'mouth change too subtle: only {n} pixels')
    return {'visual_check':'pass','changed_pixels':n,'changed_bounds':list(bounds),
            'allowed_bounds':list(expected),'source':'two emulator screenshot captures'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('closed',type=Path);p.add_argument('opened',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:r=check(a.closed,a.opened)
    except (OSError,ValueError) as e:p.error(str(e))
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
