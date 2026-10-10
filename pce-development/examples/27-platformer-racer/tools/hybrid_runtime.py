#!/usr/bin/env python3
"""Real ROM input/scene smoke with headless RPC input/run/memread/screenshot.

Uses the minimal RPC interface (no P2TR trace_frames requirement). This proves
scene transitions at debugger variables, not collision fidelity or 60 FPS.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote


def symbol(elf,name,nm):
    out=subprocess.check_output([nm,str(elf)],text=True)
    matches=re.findall(r'^([0-9a-fA-F]+)\s+[a-zA-Z]\s+'+re.escape(name)+r'$',out,re.M)
    if len(matches)!=1:raise ValueError(f'missing or duplicate ELF symbol {name}')
    n=int(matches[0],16)
    if n>>16 not in (0,0xf8):raise ValueError('symbol does not map into main RAM')
    address=n&0xffff
    if not 0x2000<=address<0x4000:raise ValueError('not in main RAM')
    return address


def run(binary,rom,addr,outdir,trace_addr):
    outdir.mkdir(parents=True,exist_ok=True)
    base=outdir/'emulator-state';base.mkdir(exist_ok=True)
    proc=subprocess.Popen([str(binary),'--rom',str(rom),'--frames','2','--rpc','--base-dir',str(base)],
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
    def rpc(command,*args):
        proc.stdin.write('\t'.join([command]+[str(x) for x in args])+'\n');proc.stdin.flush()
        line=proc.stdout.readline()
        if not line:raise RuntimeError('emulator control channel ended')
        result=json.loads(line)
        if not result.get('ok'):raise RuntimeError(f'{command}: {result.get("error")}')
        return result
    def scene():
        return int(rpc('memread',hex(addr),1,1)['hex'][:2],16)
    from p4_trace import select
    def motion():
        return select(bytes.fromhex(rpc('memread',hex(trace_addr),64,1)['hex']))
    frames=[]
    try:
        frames.append({'step':'boot','scene':scene()})
        rpc('input',0x20);rpc('run',415)
        frames.append({'step':'hold RIGHT 415 frames','scene':scene()})
        screenshot=outdir/'racing.png';screenshot.unlink(missing_ok=True);rpc('screenshot',quote(str(screenshot),safe='/'))
        rpc('input',0x10);rpc('run',163)
        frames.append({'step':'hold UP 163 frames','scene':scene()})
        screenshot2=outdir/'platformer-return.png';screenshot2.unlink(missing_ok=True);rpc('screenshot',quote(str(screenshot2),safe='/'))
        returned=motion()
        # The old smoke check stopped here, accepting a scene that froze one
        # tick later. Prove the loop and player movement actually resumed.
        rpc('input',0x80);rpc('run',20)
        continued=motion()
        frames.append({'step':'hold LEFT 20 frames after return','scene':scene(),
                       'game_frame':continued['frame'],'x_q4':continued['x_q4']})
        screenshot3=outdir/'post-return-motion.png';screenshot3.unlink(missing_ok=True)
        rpc('screenshot',quote(str(screenshot3),safe='/'))
    finally:
        try:rpc('quit')
        except Exception:proc.terminate()
        proc.wait(timeout=5)
    from PIL import Image, ImageChops
    first=Image.open(screenshot2).convert('RGB')
    final=Image.open(screenshot3).convert('RGB')
    bbox=ImageChops.difference(first,final).getbbox() if first.size==final.size else None
    changed=0
    if bbox:
        changed=sum(1 for rgb in ImageChops.difference(first,final).crop(bbox).getdata() if rgb!=(0,0,0))
    visual_ok=(bbox is not None and 20<=changed<=1024 and
               (bbox[2]-bbox[0])<=64 and (bbox[3]-bbox[1])<=32)
    expected=[0,1,0,0]
    continued_ok=continued['frame']>=returned['frame']+18 and continued['x_q4']<returned['x_q4']
    ok=[x['scene'] for x in frames]==expected and screenshot.exists() and screenshot2.exists() and screenshot3.exists() and continued_ok and visual_ok
    result={'passed':ok,'evidence':'emulator RAM scene, P4TR motion and PNG captures','frames':frames,
            'expected_scenes':expected,'racing_screenshot':str(screenshot),
            'platformer_screenshot':str(screenshot2),'post_return_screenshot':str(screenshot3),
            'post_return_motion_verified':continued_ok,'post_return_pixels_changed':changed,
            'post_return_motion_region':bbox,'post_return_visual_verified':visual_ok,
            'physics_verified':bool(continued_ok)}
    (outdir/'runtime-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if ok else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True);p.add_argument('--elf',required=True)
    p.add_argument('--emulator',default=os.getenv('PCE_HEADLESS'))
    p.add_argument('--nm',default=shutil.which('llvm-nm') or 'llvm-nm')
    p.add_argument('--out',required=True)
    a=p.parse_args()
    if not a.emulator:p.error('set PCE_HEADLESS or --emulator')
    try:sys.exit(run(Path(a.emulator).resolve(),Path(a.rom).resolve(),symbol(a.elf,'hybrid_scene',a.nm),Path(a.out).resolve(),symbol(a.elf,'p4_trace',a.nm)))
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as e:p.error(str(e))
