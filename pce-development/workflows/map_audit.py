#!/usr/bin/env python3
"""Cross-check art and collision rectangles from a shared JSON map offline."""
import argparse
import json
from pathlib import Path
import sys


def audit(data):
    errors=[];info=[]
    world=data.get('world',{});width=world.get('width');height=world.get('height');tw=world.get('tile_width',8)
    if type(width)!=int or type(height)!=int or type(tw)!=int or width<1 or height<1 or tw not in (8,16):
        return ['world requires positive width/height and 8- or 16-pixel tiles'],[]
    seen=set()
    for obj in data.get('surfaces',[]):
        if not isinstance(obj,dict):errors.append('surface is not object');continue
        name=obj.get('id')
        if not isinstance(name,str) or not name or name in seen:errors.append(f'duplicate/invalid id {name!r}')
        seen.add(name)
        boxes=[]
        for field in ('collision','art'):
            box=obj.get(field)
            if not isinstance(box,list) or len(box)!=4 or any(type(v)!=int for v in box):
                errors.append(f'{name}: {field} requires [x,y,w,h] integer pixels');boxes=[];break
            x,y,w,h=box
            if x<0 or y<0 or w<=0 or h<=0 or x+w>width or y+h>height:
                errors.append(f'{name}: {field} out of world bounds')
            boxes.append(box)
        if len(boxes)!=2:continue
        collision,art=boxes
        if abs(collision[1]-art[1])>1:
            errors.append(f'{name}: art/collision top mismatch {art[1]-collision[1]} px')
        if collision[0]<art[0] or collision[0]+collision[2]>art[0]+art[2]:
            errors.append(f'{name}: collision extends horizontally past art')
        x,y,w,h=collision
        info.append({'id':name,'left_tile':x//tw,'right_tile':(x+w-1)//tw,
                     'top_tile':y//tw,'bottom_tile':(y+h-1)//tw,
                     'collision_px':collision,'art_px':art})
    if not data.get('surfaces'):errors.append('no surfaces to audit')
    return errors,info

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');a=p.parse_args()
    try:errors,rows=audit(json.loads(Path(a.manifest).read_text()))
    except (OSError,ValueError) as exc:p.error(str(exc))
    print(json.dumps({'passed':not errors,'errors':errors,'surfaces':rows,
                      'evidence':'source manifest, not emulator rendering/collision'},indent=2))
    sys.exit(bool(errors))
