#!/usr/bin/env python3
"""Offline PC Engine / SuperGrafx SAT admission simulator (no SDK or ROM needed).

This is a planning check, not a cycle-perfect VDC emulator: positions are
visible-screen coordinates before the +32/+64 SAT bias. Sort accepted sprites
by priority *before* creating SAT entries; hardware itself doesn't reorder.
"""
import argparse
import json
from pathlib import Path

SPRITE_SIZES = {(16,16),(16,32),(16,64),(32,16),(32,32),(32,64)}


def plan(spec):
    if not isinstance(spec,dict):
        raise ValueError('input must be an object')
    size=spec.get('screen',[256,224])
    vdcs=spec.get('vdcs',1)
    if (not isinstance(size,list) or len(size)!=2 or
        any(type(v)!=int for v in size) or not (256<=size[0]<=512) or not (192<=size[1]<=240)):
        raise ValueError('screen must be [width,height] in PCE supported range')
    if type(vdcs)!=int or vdcs not in (1,2):
        raise ValueError('vdcs must be 1 (PCE) or 2 (SuperGrafx)')
    sprites=spec.get('sprites')
    if not isinstance(sprites,list) or len(sprites)>1024:
        raise ValueError('sprites must be a list with at most 1024 entries')
    seen=set()
    for item in sprites:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'] or item['id'] in seen:
            raise ValueError('sprites need unique nonempty IDs')
        seen.add(item['id'])
        for key in ('x','y','w','h','priority','vdc'):
            if type(item.get(key,0))!=int:raise ValueError('sprite '+item['id']+': '+key+' must be integer')
        if (item.get('w'),item.get('h')) not in SPRITE_SIZES:
            raise ValueError('sprite '+item['id']+': unsupported sprite dimensions')
        if not 0<=item.get('priority',0)<=255:
            raise ValueError('sprite '+item['id']+': priority outside 0..255')
        if not 0<=item.get('vdc',0)<vdcs:
            raise ValueError('sprite '+item['id']+': VDC not available')
    count=[0]*vdcs
    per_line=[[0]*size[1] for _ in range(vdcs)]
    pixels=[[0]*size[1] for _ in range(vdcs)]
    accepted=[];rejected=[]
    for item in sorted(sprites,key=lambda x:(-x.get('priority',0),x['id'])):
        x,y,w,h=(item[k] for k in ('x','y','w','h'))
        vdc=item.get('vdc',0)
        top=max(0,y);bottom=min(size[1],y+h)
        visible=top<bottom and x<size[0] and x+w>0
        if not visible:
            rejected.append({'id':item['id'],'reason':'offscreen'});continue
        if count[vdc]>=64:
            rejected.append({'id':item['id'],'reason':'sat_64'});continue
        if any(per_line[vdc][line]>=16 for line in range(top,bottom)):
            rejected.append({'id':item['id'],'reason':'scanline_16'});continue
        # Hardware sprite processing counts full sprite width, even when the
        # sprite is clipped by the screen edges.
        if any(pixels[vdc][line]+w>256 for line in range(top,bottom)):
            rejected.append({'id':item['id'],'reason':'scanline_256_pixels'});continue
        for line in range(top,bottom):
            per_line[vdc][line]+=1;pixels[vdc][line]+=w
        count[vdc]+=1
        accepted.append({'id':item['id'],'vdc':vdc,'sat_slot':count[vdc]-1})
    return {'accepted':accepted,'rejected':rejected,
            'accepted_count':len(accepted),'dropped_count':len(rejected),
            'per_vdc':[{'vdc':v,'sprites':count[v], 'peak_scanline_sprites':max(per_line[v]),
                        'peak_scanline_pixels':max(pixels[v])} for v in range(vdcs)],
            'note':'planning aid, not measured hardware SAT timings or an emulator screenshot'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--strict',action='store_true',help='nonzero exit if any on-screen sprite is rejected')
    args=parser.parse_args()
    try:
        result=plan(json.loads(args.spec.read_text()))
    except (ValueError,OSError) as err:
        parser.error(str(err))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 1 if args.strict and any(r['reason']!='offscreen' for r in result['rejected']) else 0


if __name__=='__main__':
    raise SystemExit(main())
