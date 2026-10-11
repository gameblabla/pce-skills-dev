#!/usr/bin/env python3
"""G2TR v2: deterministic offline validation and optional headless emulator trace.

P2TR v1 platformer records and platformer_trace.py are preserved unchanged.
G2TR stores generic telemetry at 64 bytes per slot, two slots in main RAM.
"""
import argparse
import json
import pathlib
import struct
import sys
from collections import Counter

FORMAT = struct.Struct('<4sBBBBIHH12i')
assert FORMAT.size == 64
GENRES = {1:'platformer', 2:'shmup', 3:'raycaster', 4:'racing', 5:'visual_novel'}
BUTTONS = {'i':0,'ii':1,'select':2,'run':3,'up':4,'right':5,'down':6,'left':7,
           'iii':8,'iv':9,'v':10,'vi':11}


def decode(raw):
    if len(raw) != 64:
        raise ValueError('G2TR record must contain exactly 64 bytes')
    d = FORMAT.unpack(raw)
    if d[0] != b'G2TR' or d[1] != 2:
        raise ValueError('unknown G2TR magic or version')
    if d[2] not in GENRES:
        raise ValueError('unknown G2TR genre')
    if d[7] & 1:
        raise ValueError('partial publication: odd sequence')
    keys = ('x', 'y', 'vx', 'vy', 'camera_x', 'camera_y', 'screen_x', 'screen_y')
    result = dict(frame=d[5],genre=GENRES[d[2]],scene=d[3],flags=d[4],buttons=d[6],seq=d[7])
    result.update({k:round(v/256,3) for k,v in zip(keys,d[8:16])})
    result['state'] = list(d[16:20])
    return result


def choose(buffer):
    if len(buffer) != 128:
        raise ValueError('G2TR trace window must be two 64-byte records')
    records = []
    for slot in (buffer[:64],buffer[64:]):
        try:
            records.append(decode(slot))
        except ValueError:
            continue
    if not records:
        raise ValueError('no complete G2TR record in the trace window')
    return max(records, key=lambda r:(r['frame'], r['seq']))


EVENTS = {
    'shmup_enemy_hit', 'shmup_player_damage', 'ray_wall_blocked',
    'racing_checkpoint', 'racing_lap', 'racing_traffic_hit'
}


def interaction_audit(samples, scenario):
    """Verify *observable transitions*, not just changing telemetry numbers.

    Every event is backed by adjacent sampled ticks (max 3-frame gap). Offline map validation
    additionally guards against crossing a solid raycaster tile.
    """
    issues = []
    observed = {name: [] for name in EVENTS}
    required = scenario.get('require_events', [])
    if not isinstance(required, list) or len(required) != len(set(required)) or any(
            name not in EVENTS for name in required):
        raise ValueError('require_events must be unique names from: ' + ', '.join(sorted(EVENTS)))
    world = scenario.get('world_map')
    if world is not None:
        if not isinstance(world,list) or not world or len(world)>64 or not world[0] or any(
                not isinstance(row,str) or len(row)!=len(world[0]) or len(row)>64 or
                any(ch not in '.#' for ch in row) for row in world):
            raise ValueError('world_map must be a rectangular array of . and # rows (<=64x64)')
        for s in samples:
            if s['genre'] != 'raycaster':continue
            ix,iy=int(s['x']//1),int(s['y']//1)
            if not (0<=iy<len(world) and 0<=ix<len(world[0])) or world[iy][ix]=='#':
                issues.append({'frame':s['frame'],'code':'entered_solid_wall',
                               'detail':f'raycaster position ({s["x"]},{s["y"]}) lies in wall/outside map'})
    last_checkpoint_frame = None
    for p,s in zip(samples,samples[1:]):
        if not 0 < s['frame']-p['frame'] <= 3 or s['genre']!=p['genre'] or s['scene']!=p['scene']:
            continue
        colliding=bool(s['flags'] & 4)
        transition=bool(s['flags'] & 8)
        v,w=p['state'],s['state']
        if s['genre']=='shmup':
            if w[1]<v[1]:
                if colliding and w[2]>0:
                    observed['shmup_enemy_hit'].append(s['frame'])
                else:
                    issues.append({'frame':s['frame'],'code':'enemy_disappeared_without_hit',
                                   'detail':'enemy count fell without recorded collision and player shot'})
            if w[3]>v[3]:
                if colliding:observed['shmup_player_damage'].append(s['frame'])
                else:issues.append({'frame':s['frame'],'code':'damage_without_collision',
                                    'detail':'damage increased without collision flag'})
        if s['genre']=='raycaster' and colliding:
            if s['buttons'] & ((1<<4)|(1<<6)):
                observed['ray_wall_blocked'].append(s['frame'])
        if s['genre']=='racing':
            old_checkpoint=v[1]//(64*256)
            new_checkpoint=w[1]//(64*256)
            if new_checkpoint>old_checkpoint:
                last_checkpoint_frame=s['frame']
                if transition:observed['racing_checkpoint'].append(s['frame'])
                else:issues.append({'frame':s['frame'],'code':'checkpoint_not_published',
                                    'detail':'crossed 64-unit checkpoint without transition flag'})
            elif transition and (last_checkpoint_frame is None or
                                 s['frame']-last_checkpoint_frame>3):
                issues.append({'frame':s['frame'],'code':'spurious_checkpoint',
                               'detail':'transition flagged without a checkpoint in the last 3 game ticks'})
            if w[1]//(256*256)>v[1]//(256*256) and transition:
                observed['racing_lap'].append(s['frame'])
            if colliding:
                observed['racing_traffic_hit'].append(s['frame'])
    for name in required:
        if not observed[name]:
            issues.append({'frame':None,'code':'required_event_missing',
                           'detail':name+' was not observed in adjacent captured game frames'})
    return issues, {k: {'count':len(v),'first_frame':v[0] if v else None}
                    for k,v in sorted(observed.items()) if v or k in required}


def validate(samples, scenario=None):
    """Verify genre invariants; issues are evidence of suspicious authored telemetry."""
    issues=[]
    def add(s,code,detail):
        issues.append({'frame':s['frame'],'code':code,'detail':detail})
    genres=set()
    for i,s in enumerate(samples):
        genres.add(s['genre'])
        if i and s['frame'] < samples[i-1]['frame']:
            add(s,'frame_regression','game frame went backwards')
        if i and s['frame']==samples[i-1]['frame'] and s['seq']!=samples[i-1]['seq']:
            add(s,'frame_not_advanced','sequence advanced without frame advance')
        # Invisible actors (or instrumentation-only probes) are legitimate.
        # A trace's visibility flag must never be mistaken for screenshot evidence.
        if s['genre'] in ('platformer','shmup','racing') and (s['flags'] & 1):
            expect=s['x']-s['camera_x']
            if abs(s['screen_x']-expect)>1:
                add(s,'camera_x_mismatch',f'draw x={s["screen_x"]}, expected world-camera={expect:.2f}')
        v=s['state']
        if s['genre']=='shmup':
            if any(n<0 for n in v):
                add(s,'negative_shmup_counter','bullet/enemy/shot/damage counters must be nonnegative')
            if v[0]>64:
                add(s,'sat_budget','more than 64 live bullets reported; verify SAT allocation')
        elif s['genre']=='raycaster':
            if v[0] <= 0 or v[1]>v[0] or v[1]<0:
                add(s,'ray_columns_invalid','rays cast/hit must be nonnegative and hits <= casts')
            if v[2]<0 or v[3]<v[2]:
                add(s,'ray_depth_invalid','near/far ray depth out of order')
        elif s['genre']=='racing':
            if v[2]<0:
                add(s,'negative_speed','racing forward speed is negative')
            if v[3]>64 or v[3]<0:
                add(s,'race_objects_invalid','visible object count is outside 0..64')
        elif s['genre']=='visual_novel':
            if min(v)<0 or v[2] not in (0,1):
                add(s,'vn_state_invalid','background, portrait, mouth, dialogue IDs must be valid')
            if v[1]==0 and v[2]:
                add(s,'mouth_without_portrait','mouth animated when no portrait is present')
        elif s['genre']=='platformer' and v[0] not in (0,1):
            add(s,'grounded_invalid','grounded state is not Boolean')
        if i and s['genre']==samples[i-1]['genre'] and s['frame'] == samples[i-1]['frame']+1:
            p=samples[i-1]
            if s['genre']=='racing' and s['state'][1]<p['state'][1] and s['state'][2]>=0:
                add(s,'racing_progress_reverse','progress went backwards while forward speed is nonnegative')
            if s['genre']=='shmup' and s['state'][2]<p['state'][2]:
                add(s,'shots_counter_reset','shots fired decreased in the same scene')
            if s['genre']=='visual_novel' and s['scene']==p['scene'] and s['state'][3]<p['state'][3]:
                add(s,'dialogue_regressed','dialogue ID went backwards without a scene change')
    if scenario:
        steps=scenario.get('steps',[])
        if not isinstance(steps,list) or not 1<=len(steps)<=32:
            raise ValueError('scenario needs 1..32 steps')
        if sum(int(s.get('frames',0)) for s in steps)>3600:
            raise ValueError('scenario exceeds 3600 frames')
        for s in steps:
            if not 1<=s.get('frames',0)<=3600 or any(b not in BUTTONS for b in s.get('buttons',[])):
                raise ValueError('invalid step frames/buttons')
            if len(set(s.get('buttons',[])))!=len(s.get('buttons',[])):
                raise ValueError('duplicate buttons')
        if sum(s['frames'] for s in steps)>len(samples):
            issues.append({'frame':None,'code':'incomplete_trace','detail':'fewer samples than the scenario requests'})
        required=scenario.get('require_genres',[])
        for name in required:
            if name not in GENRES.values():
                raise ValueError('unknown required genre: '+str(name))
            if name not in genres:
                issues.append({'frame':None,'code':'missing_genre','detail':name+' did not appear'})
        variation=scenario.get('require_state_variation',{})
        for name,indices in variation.items():
            if name not in GENRES.values() or not isinstance(indices,list) or any(not isinstance(i,int) or not 0<=i<4 for i in indices):
                raise ValueError('state variation must map known genres to state indices 0..3')
            for index in indices:
                vals={s['state'][index] for s in samples if s['genre']==name}
                if len(vals)<2:
                    issues.append({'frame':None,'code':'state_not_changing',
                                   'detail':f'{name} state[{index}] stayed constant or was not sampled'})
    events={}
    if scenario:
        extra,events=interaction_audit(samples,scenario)
        issues.extend(extra)
    return {'trace_format':'G2TR v2','samples':len(samples),'genres':sorted(genres),
            'interaction_evidence':events,'issues':issues,'issue_counts':dict(Counter(i['code'] for i in issues)),
            'note':'game-authored RAM telemetry, not independent evidence of rendered pixels, audio or actual hardware'}


def encode_for_test(genre,frame=1,scene=1,flags=1,buttons=0,sequence=2,
                    x=0,y=0,vx=0,vy=0,camera_x=0,camera_y=0,screen_x=0,screen_y=0,state=(0,0,0,0)):
    gid=next(k for k,v in GENRES.items() if v==genre)
    q=[round(z*256) for z in (x,y,vx,vy,camera_x,camera_y,screen_x,screen_y)]
    return FORMAT.pack(b'G2TR',2,gid,scene,flags,frame,buttons,sequence,*q,*state)


def run_emulator(rom,address,scenario,bios=None,base_dir=None,initial_frames=2,samples_output=None):
    import platformer_trace as old
    if address<0x2000 or address+128>0x4000:
        raise ValueError('128-byte window must fit within $2000..$3FFF')
    steps=scenario['steps']
    validate([],scenario) # Check step spelling/duration before launching
    exe=old._find_binary(rom)
    base_dir=pathlib.Path(base_dir or 'build/genre-trace-base').resolve()
    base_dir.mkdir(parents=True,exist_ok=True)
    # Optional explicit boot warmup: the VRAM-resident 128x128 example
    # initializes 8,192 BAT words and 256 tile patterns before game ticks.
    # Those display setup frames are not part of the interaction scenario.
    boot_frames=scenario.get('boot_frames',initial_frames)
    if not isinstance(boot_frames,int) or not 1<=boot_frames<=600:
        raise ValueError('boot_frames must be an integer from 1 to 600')
    client=old.NativeControl(str(exe),rom,base_dir,bios,boot_frames)
    samples=[]
    try:
        for step in steps:
            mask=sum(1<<BUTTONS[b] for b in step.get('buttons',[]))
            client.call('input',mask)
            # Generic RPC: existing trace_frames is intentionally hard-coded to
            # two 216-byte platformer records. G2TR uses run + memread instead.
            for _ in range(step['frames']):
                for attempt in range(16):
                    client.call('run',1)
                    pair=bytes.fromhex(client.call('memread',hex(address),128,1)['hex'])
                    try:
                        state=choose(pair)
                    except ValueError:
                        state=None
                    if state and (not samples or state['frame']>samples[-1]['frame']):
                        samples.append(state)
                        break
                else:
                    raise RuntimeError('G2TR frame did not advance within sixteen emulator frames; inspect publication, IRQ and heavy rendering')
    finally:
        client.close()
    if samples_output:
        target=pathlib.Path(samples_output)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(samples,indent=2)+'\n')
    return validate(samples,scenario)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=pathlib.Path,help='JSON list of decoded G2TR frames (offline)')
    p.add_argument('--rom',help='ROM/ISO for RPC trace')
    p.add_argument('--elf',help='ELF for G2TR symbol resolution')
    p.add_argument('--symbol',default='pce_genre_trace')
    p.add_argument('--address',help='main-RAM address, e.g. 0x2800')
    p.add_argument('--scenario',type=pathlib.Path)
    p.add_argument('--output',type=pathlib.Path)
    p.add_argument('--samples-output',type=pathlib.Path,help='write decoded per-tick frames for offline replay/auditing')
    args=p.parse_args()
    try:
        spec=json.loads(args.scenario.read_text()) if args.scenario else None
        if args.rom:
            if not spec:
                raise ValueError('--scenario is required for emulator run')
            from platformer_trace import resolve_trace_address
            addr=int(args.address,0) if args.address else resolve_trace_address(args.elf or args.rom+'.elf',args.symbol)
            if addr>0xFFFF and addr>>16==0xF8: addr &= 0xFFFF
            result=run_emulator(args.rom,addr,spec,samples_output=args.samples_output)
        else:
            if not args.trace:
                raise ValueError('provide --trace JSON or --rom')
            data=json.loads(args.trace.read_text())
            records=[decode(bytes.fromhex(x['hex'])) if 'hex' in x else x for x in data]
            result=validate(records,spec)
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        return 1 if result['issues'] else 0
    except (ValueError,OSError,KeyError,RuntimeError) as exc:
        p.error(str(exc))

if __name__=='__main__':
    sys.exit(main())
