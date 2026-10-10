#!/usr/bin/env python3
"""Audit an author-provided animation manifest offline; never claims rendered frames exist."""
import argparse
import json
from pathlib import Path
import re
import sys

REQUIRED={'idle','run','jump','shoot_idle','shoot_run','hurt','death'}

def audit(doc):
    errors=[]
    states=doc.get('states')
    if not isinstance(states,dict):return ['states must be an object']
    missing=REQUIRED-set(states)
    if missing:errors.append('missing states: '+','.join(sorted(missing)))
    referenced={}
    for name,entry in states.items():
        if not re.fullmatch('[a-z][a-z0-9_]*',name):errors.append(f'invalid state name {name!r}')
        if not isinstance(entry,dict):errors.append(f'{name}: state must be object');continue
        frames=entry.get('frames');ticks=entry.get('ticks_per_frame')
        if not isinstance(frames,list) or not frames or len(frames)>64:errors.append(f'{name}: need 1..64 frames');continue
        if type(ticks)!=int or not 1<=ticks<=60:errors.append(f'{name}: ticks_per_frame must be 1..60')
        for index,frame in enumerate(frames):
            if not isinstance(frame,str) or not re.fullmatch('[A-Za-z0-9_/.-]+',frame) or frame.startswith('/') or '..' in Path(frame).parts:
                errors.append(f'{name}: unsafe frame path at {index}');continue
            referenced.setdefault(frame,[]).append(name)
    if doc.get('require_existing_files'):
        root=Path(doc.get('asset_root','.')).resolve()
        for frame in referenced:
            file=(root/frame).resolve()
            if not file.is_relative_to(root) or not file.is_file():errors.append(f'missing/unsafe referenced asset: {frame}')
    return errors

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');a=p.parse_args()
    try:errors=audit(json.loads(Path(a.manifest).read_text()))
    except (OSError,ValueError) as exc:p.error(str(exc))
    print(json.dumps({'passed':not errors,'errors':errors,'evidence':'manifest only; not runtime animation'},indent=2))
    sys.exit(bool(errors))
