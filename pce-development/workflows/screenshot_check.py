#!/usr/bin/env python3
"""Offline visual smoke comparisons; does NOT assert animation, collision, audio, or physics."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops


def metrics(file):
    im=Image.open(file).convert('RGB')
    colors=im.getcolors(im.width*im.height) or []
    background=max(colors,key=lambda a:a[0])[1] if colors else None
    changed=sum(n for n,rgb in colors if rgb!=background)
    return {'size':[im.width,im.height],'unique_colors':len(colors),
            'non_dominant_pixels':changed,'dominant_color':background}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image');ap.add_argument('--min-colors',type=int,default=2)
    ap.add_argument('--min-non-background',type=int,default=50)
    ap.add_argument('--compare');ap.add_argument('--min-changed',type=int,default=1)
    a=ap.parse_args();m=metrics(a.image)
    errors=[]
    if m['unique_colors']<a.min_colors:errors.append('too few colours')
    if m['non_dominant_pixels']<a.min_non_background:errors.append('image may be blank')
    if a.compare:
        x=Image.open(a.image).convert('RGB');y=Image.open(a.compare).convert('RGB')
        if x.size!=y.size:errors.append('different image sizes')
        else:
            diff=ImageChops.difference(x,y)
            m['changed_pixels']=sum(1 for px in (diff.get_flattened_data() if hasattr(diff, 'get_flattened_data') else diff.getdata()) if any(px))
            if m['changed_pixels']<a.min_changed:errors.append('insufficient visual change')
    print(json.dumps({'metrics':m,'passed':not errors,'errors':errors},indent=2))
    return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
