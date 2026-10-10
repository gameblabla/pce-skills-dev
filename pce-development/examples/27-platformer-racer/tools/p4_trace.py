#!/usr/bin/env python3
"""P4TR v4: 16-bit Q4 game trace with external world geometry and input replay.

Does not require the emulator's hard-coded P2TR trace_frames RPC. The trace is
64 bytes TOTAL, two 32-byte records, read using generic memread/run commands.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys
from headless_rpc import NativeControl,executable,symbol

RECORD=struct.Struct('<4s6BH5h2h2H2B')
assert RECORD.size==32
BUTTONS={'i':0,'ii':1,'select':2,'run':3,'up':4,'right':5,'down':6,'left':7}

def decode(record):
    if len(record)!=32:raise ValueError('P4TR record must be 32 bytes')
    v=RECORD.unpack(record)
    if v[0]!=b'P4TR' or v[1]!=4 or (v[5]&1):raise ValueError('invalid or partial P4TR publication')
    keys=('x_q4','y_q4','vx_q4','vy_q4','camera_q4','draw_x','draw_y',
          'race_lane','race_progress','surface_count','live_sprites')
    result=dict(version=v[1],scene=v[2],flags=v[3],events=v[4],sequence=v[5],
                buttons=v[6],frame=v[7])
    result.update(zip(keys,v[8:]))
    return result

def select(raw):
    if len(raw)!=64:raise ValueError('P4TR window must be exactly 64 bytes')
    candidates=[]
    for at in (0,32):
        try:candidates.append(decode(raw[at:at+32]))
        except ValueError:continue
    if not candidates:raise ValueError('both P4TR slots invalid or in progress')
    return max(candidates,key=lambda s:(s['frame'],s['sequence']))

def geometry(path):
    text=Path(path).read_text()
    def constant(name):
        m=re.search(r'^#define\s+'+name+r'\s+(\d+)\s*$',text,re.M)
        if not m:raise ValueError('missing platform layout constant '+name)
        return int(m.group(1))
    rows=re.findall(r'\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}',text)
    if len(rows)!=constant('PCE_DEMO_SURFACE_COUNT'):raise ValueError('C platform count differs from parsed geometry')
    items=[tuple(map(int,r)) for r in rows]
    if not items or any(w<=0 or h<=0 or art<=0 or x<0 or x+w>constant('PCE_DEMO_WORLD_WIDTH') for x,y,w,h,art in items):
        raise ValueError('invalid platform geometry')
    return {'world_width':constant('PCE_DEMO_WORLD_WIDTH'),'surfaces':items}

def audit(samples,layout,require_hybrid=False):
    """Analyze actual game state, against *separate* map geometry, never trace-authored surfaces."""
    failures=[]
    def add(s,reason):failures.append({'frame':s['frame'],'issue':reason})
    last=None
    transitions=[];events={'landed':0,'jumped':0,'blocked_x':0,'race':0}
    width=layout['world_width']
    for s in samples:
        if s['frame']<1 or s['scene'] not in (0,1):add(s,'invalid_scene_or_frame')
        if s['surface_count']!=len(layout['surfaces']):add(s,'surface_count_drift')
        if s['live_sprites']!=(2 if s['scene']==1 else 1):add(s,'SAT_ownership_mismatch')
        if not 0<=s['y_q4']<=224*16:add(s,'player_y_outside_world')
        if not 0<=s['x_q4']<=(width-16)*16:add(s,'player_x_outside_world')
        if not 0<=s['camera_q4']<=(width-256)*16:add(s,'camera_outside_world')
        if s['scene']==0:
            target=max(0,min((width-256)*16,s['x_q4']-104*16))
            if s['camera_q4']!=target:add(s,'camera_follow_mismatch')
            expected_x=(s['x_q4']-s['camera_q4'])//16+3
            expected_y=s['y_q4']//16+1
            if s['draw_x']!=expected_x or s['draw_y']!=expected_y:add(s,'visual_collision_box_mismatch')
            if abs(s['vx_q4'])>16 or not -80<=s['vy_q4']<=96:add(s,'velocity_out_of_bounds')
            if s['flags']&1:
                feet=s['y_q4']+16*16
                if not any(feet==y*16 and s['x_q4']+13*16>x*16 and s['x_q4']+3*16<(x+w)*16
                           for x,y,w,_,_ in layout['surfaces']):add(s,'grounded_without_support')
                if s['vy_q4']!=0:add(s,'grounded_with_vertical_velocity')
            if s['events']&1:
                events['landed']+=1
                if not(s['flags']&1):add(s,'landed_without_grounded')
            if s['events']&2:
                events['jumped']+=1
                if s['flags']&1 or s['vy_q4']>=0:add(s,'jumped_without_upward_velocity')
            if s['flags']&4:events['blocked_x']+=1
        else:
            events['race']+=1
            if not 48<=s['race_lane']<=208:add(s,'racing_lane_out_of_bounds')
            if not 0<=s['race_progress']<=480:add(s,'racing_progress_out_of_bounds')
        if last:
            if not 1<=s['frame']-last['frame']<=16:add(s,'frame_gap_or_regression')
            if s['scene']!=last['scene']:
                transitions.append([last['scene'],s['scene']])
                if s['scene']==1 and s['x_q4']<440*16:add(s,'entered_race_before_platform_end')
                if s['scene']==0 and s['race_progress']<480:add(s,'race_return_before_finish')
            elif s['scene']==0:
                gap=s['frame']-last['frame']
                if abs(s['x_q4']-last['x_q4'])>16*gap:add(s,'teleport_x')
                if gap<=3 and not(last['flags']&1) and (s['flags']&1) and not(s['events']&1):
                    add(s,'landing_event_missing')
                if gap<=3 and (last['flags']&1) and not(s['flags']&1) and s['vy_q4']<0 and not(s['events']&2):
                    add(s,'jump_event_missing')
            elif s['race_progress']<last['race_progress']:
                add(s,'race_progress_reversed')
        last=s
    if require_hybrid and (transitions[:2]!=[[0,1],[1,0]]):
        failures.append({'frame':None,'issue':'missing_platformer_racer_roundtrip'})
    return dict(ok=not failures,frames=len(samples),events=events,transitions=transitions,
                issues=failures,format='P4TR v4',note='Trace is authored by the ROM; visual evidence still required.')

def scenario_steps(spec):
    if not isinstance(spec,list) or not 1<=len(spec)<=40:raise ValueError('scenario needs 1..40 steps')
    result=[]
    for step in spec:
        count=step.get('frames');buttons=step.get('buttons',[])
        if not isinstance(count,int) or not 1<=count<=3600:raise ValueError('bad frames')
        if not isinstance(buttons,list) or len(buttons)!=len(set(buttons)) or any(b not in BUTTONS for b in buttons):
            raise ValueError('bad or duplicate button')
        result.append((count,sum(1<<BUTTONS[b] for b in buttons)))
    if sum(f for f,_ in result)>3600:raise ValueError('scenario >3600 frames')
    return result

def run(rom,elf,scenario,base_dir):
    steps=scenario_steps(scenario)
    address=symbol(elf)
    base_dir.mkdir(parents=True,exist_ok=True)
    client=NativeControl(executable(),rom,base_dir)
    samples=[]
    try:
        for frames,mask in steps:
            client.call('input',mask)
            for _ in range(frames):
                for _retry in range(24):
                    client.call('run',1)
                    try:state=select(bytes.fromhex(client.call('memread',hex(address),64,1)['hex']))
                    except ValueError:continue
                    if not samples or state['frame']>samples[-1]['frame']:
                        samples.append(state);break
                else:raise RuntimeError('P4TR did not advance within 24 emulator frames; last='+str(samples[-1] if samples else None))
    finally:client.close()
    return samples

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom');ap.add_argument('--elf')
    ap.add_argument('--scenario');ap.add_argument('--layout',default='assets/platform_layout.h')
    ap.add_argument('--samples',help='Offline trace JSON replay')
    ap.add_argument('--samples-out');ap.add_argument('--base-dir',default='build/p4-trace-base')
    ap.add_argument('--output',default='build/p4-trace-report.json')
    ap.add_argument('--hybrid',action='store_true')
    args=ap.parse_args()
    try:
        if args.samples:samples=json.loads(Path(args.samples).read_text())
        else:
            if not args.rom or not args.elf or not args.scenario:raise ValueError('need --rom, --elf, --scenario for native run')
            samples=run(args.rom,args.elf,json.loads(Path(args.scenario).read_text()),Path(args.base_dir))
        if args.samples_out:
            dest=Path(args.samples_out);dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(samples,indent=2)+'\n')
        report=audit(samples,geometry(args.layout),args.hybrid)
        dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        return 0 if report['ok'] else 1
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        ap.error(str(exc))
if __name__=='__main__':sys.exit(main())
