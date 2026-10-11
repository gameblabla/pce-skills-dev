#!/usr/bin/env python3
"""Offline PC Engine project router, bring-up checker, scaffolder, spec validator and header generator.

No model, web request, commercial ROM, firmware or image generator is used here.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
RECIPES = {
    'platformer': '26-platformer-starter',
    'hybrid': '27-platformer-racer',
    'racer': '86-mode7-bitmap-floor',
    'math': '95-cpu-mul8',
    'audio': '03-psg-tone',
    'graphics': '85-bitmap-128-circle',
    'sprite': '78-vdc-one-sprite',
    'cd': '01-cdrom2-hello',
    'sgx': '18-supergrafx-vdc2',
    'base': '00-project-template',
    'level': '28-generated-level',
    'visual_novel':'29-visual-novel',
    'shmup':'33-rendered-shmup',
    'raycaster_visual':'34-rendered-raycaster',
    'racing_visual':'35-rendered-racer',
    'raycaster_trace':'31-raycaster-trace-probe',
    'shmup_trace':'30-shmup-trace-probe',
    'raycaster':'31-raycaster-trace-probe',
    'racing_trace':'32-racing-trace-probe',
}


def fail(message):
    raise ValueError(message)


def choose(prompt):
    q = prompt.lower()
    has_platform = bool(re.search(r'platform|contra|run.?and.?gun|jump', q))
    has_trace=bool(re.search(r'\b(trace|tracing|telemetry|g2tr|p2tr|debug|debugging)\b', q))
    if re.search(r'visual.?novel|dialogue|mouth.?animat|portrait|character.?conversation',q):
        return 'visual_novel'
    if re.search(r'raycast|wolfenstein|pseudo.?3d.*wall',q):
        return 'raycaster_trace' if has_trace else 'raycaster_visual'
    if re.search(r'shmup|shoot.?em.?up|bullet.?hell|scrolling.?shooter',q):
        return 'shmup_trace' if has_trace else 'shmup'
    if has_trace and re.search(r'rac(e|ing|er)|driv|road|lane',q) and not has_platform:
        return 'racing_trace'
    has_race = bool(re.search(r'rac(e|ing|er)|driv|car|road', q))
    if has_platform and has_race:
        return 'hybrid'
    if has_platform:
        return 'platformer'
    if has_race:
        return 'racer' if re.search(r'mode.?7|bitmap|paired.?bat|512.?x.?224',q) else 'racing_visual'
    if re.search(r'\b(fast.?math|multiply|multiplication|division|divid|libcommon|software.?math|16.?bit.?math)\b',q):return 'math'
    for key, pat in [('level', r'asset.?pack|tile.?map|tile.?set|level.?generator|level.?editor|generated map'),
                     ('audio', r'psg|sound|music|tone|audio'),
                     ('cd', r'cd.?rom|system card|disc|ipl'),
                     ('sgx', r'supergrafx|sgx|vdc2'),
                     ('sprite', r'sprite|satb|animation'),
                     ('graphics', r'bitmap|mode.?7|graphics|palette')]:
        if re.search(pat,q): return key
    return 'base'


def guidance(kind, request=""):
    proj=RECIPES[kind]
    requested_cd=bool(re.search(r'super\s*cd|cd.?rom|disc|system card|\bcd\b',request,re.I))
    is_micro = kind in ('audio','racer','graphics','sprite','sgx','math')
    path=('examples/micro/' if is_micro else 'examples/')+proj
    lines=['Inspect AGENTS.md and SKILL.md before editing.',
           f'Copy {path} through offline.py new; never edit a reference example in place.',
           'Run make, then make run; for instrumented starters use make trace and genre-specific validators.',
           'Use real game state and fresh emulator captures; compiler success is not gameplay proof.',
           'Check linker map, RAM, IRQ/PSG channel ownership before combining subsystems.',
           'Run model_guard.py scan on src before building; classify compiler errors with model_guard.py diagnose LOG.',
           'For new target C code use only 8/16-bit integers. Run make arith-check offline, then inspect the compiled ELF with arith_guard.py elf.',
           'Do not claim a working CD, player controls, or 60-second level based on a HuCard screenshot.']
    if kind=='hybrid':
        lines+=['Run make rules-check and make simulate for the hybrid JSON spec.',
                'Keep collision/world coordinates independent of camera and art.',
                'Trace jump/landing/input edges via compact P4TR v4; audit transitions and post-return movement.']
    if kind=='platformer':
        lines+=['Use make trace for 16-bit P4TR walk/jump/landing; no 32-bit ABI or specialized trace_frames RPC.',
                'Keep collision/world coordinates independent of camera and art.']
    if kind=='math': lines+=['Use libcommon/include/pce_fastmath.h and link libpcecommon.a rather than compiler software multiply/divide.',
                                'For Mode7, use generated projection lookups; do NOT calculate reciprocal or 16-bit division each line.',
                                'Generic shift/subtract division is correctness-first, not benchmarked to be faster than compiler-rt.']
    if kind=='audio': lines+=['Never add VDC/VCE/font/sprite drawing to an audio recipe.']
    if kind in ('raycaster_trace','racing_trace','shmup_trace'):
        lines+=['This is an instrumentation-only G2TR probe; it does NOT draw a playable game.',
                'Run make trace with a headless emulator supporting run/input/memread; check source and graphics separately.',
                'G2TR state[0..3] must be real game values; for modern platformer projects use compact P4TR with independent geometry.']
    if kind=='raycaster_visual':
        lines+=['Raycaster: Example implementation. Not speed optimized, has issues.',
                'Use only the 128x128 progressive paired-BAT mode. Run make raster-sweep and bitmap-stress before shipping changes.',
                'Use workflows/paired_bat_plan.py --mode full for the BAT address proof. This is not true atomic frame presentation.']
    if kind=='visual_novel':
        lines+=['Edit assets/background.png and transparent 16x16 mouth overlays; make assets regenerates C and memory report.',
                'Use make assets-multi for high-colour 16-background-palette mode (Pillow+numpy required).',
                'Run make trace and make visual-test. One closed/open screenshot pair must differ ONLY in the mouth region.',
                'Do not call PNG previews emulator screenshots; use original static scene + separate sprite and SAT.']
    if kind in ('shmup','raycaster_visual','racing_visual'):
        lines+=['This is a minimal *rendered* gameplay lesson, not a complete game or a Super CD image.',
                'Run make trace AND make visual-test to compare input-driven telemetry with emulator screenshots.',
                'Edit the validated 256x224 PNG/64x16 atlas and run make assets for shmup/racing; raycaster draws actual BAT walls.',
                'Keep the nonvisual G2TR probes for hardware-independent state debugging.',
                'Run the VRAM manifest audit on PNG-packed scenes and split raster-active uploads into <=16-byte bursts.',
                'Run a strict linked-ELF arithmetic audit; the rendered genre examples require zero software divide/multiply helpers.']
    if kind=='level': lines+=['Edit assets/level.json, run make assets-check then make. Each cell is an 8x8 tile, not a pixel.',
                             'The rendered level has no playable enemies or goal logic: link it to example 26, then test actual events.']
    if is_micro: lines+=['Micro recipe scaffolds the shared micro and starter build helpers.']
    if kind=='cd': lines+=['A .bin is not a bootable CD image; cold-boot with IPL and user-provided BIOS.']
    if kind=='platformer': lines+=['Example 26 is a physics baseline, NOT a complete title/enemy/stomp/flag/fade game.',
                                  'Use generated assets (example 28) and an explicit scene-state acceptance checklist before claiming a full game.']
    if requested_cd and kind!='cd':
        lines+=['TARGET WARNING: The selected game starter is a HuCard preview, not a Super CD-ROM2 disc.',
                'Build and cold-boot an IPL + CD image with user-provided BIOS before claiming a Super CD game.']
    return {'recipe':kind,'project':path,
            'requested_target':'supercd' if requested_cd else 'hucard',
            'starter_target':'hucard',
            'target_matches_request':not requested_cd,
            'instructions':lines,
            'first_commands':[f'python3 pce-development/workflows/offline.py new --recipe {kind} --out ./my-pce-project',
                              'cd my-pce-project && make',
                              'make run']}


def agent_brief(prompt):
    plan=guidance(choose(prompt), prompt); rules=plan['instructions']
    return ('# PC Engine local-model implementation brief\n\n'
            'Requested behavior: '+prompt.strip().replace('\n',' ')+'\n\n'
            'Use the existing verified recipe: `'+plan['project']+'`.\n\n'
            '## Required sequence\n\n'+''.join(f'{i}. {instruction}\n' for i,instruction in enumerate(rules,1))+
            '\n## Exact commands\n\n```sh\n'+ '\n'.join(plan['first_commands'])+'\n```\n\n'
            '## Completion evidence\n\n'
            '- Built artifact (compiler, map, ROM identity and target type).\n'
            '- Host-only spec validation/simulation, labelled as such.\n'
            '- Emulator scripted input/trace and screenshot if RPC supports it.\n'
            '- Unverified features stated explicitly. No invented passes or screenshots.\n')


def parse_spec(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,dict): fail('spec must be an object')
    if data.get('version')!=1: fail('version must be 1')
    world=data.get('world'); controls=data.get('controls'); scenes=data.get('scenes')
    if not isinstance(world,dict) or not isinstance(controls,dict) or not isinstance(scenes,list):
        fail('world, controls and scenes are required')
    def integer(obj,key,lo,hi):
        v=obj.get(key)
        if type(v) is not int or not lo<=v<=hi: fail(f'{key} must be integer in [{lo}, {hi}]')
        return v
    width=integer(world,'width',256,8192); height=integer(world,'height',224,4096)
    integer(controls,'walk_speed_q8',1,4096)
    integer(controls,'gravity_q8',1,2048)
    integer(controls,'jump_velocity_q8',-4096,-1)
    integer(controls,'race_speed_q8',1,4096)
    lane_left=integer(controls,'race_lane_left',0,255)
    lane_right=integer(controls,'race_lane_right',lane_left+16,255)
    if len(scenes)!=2:fail('the runnable hybrid demo supports exactly two scenes; extend its C state machine before adding more')
    names=[]
    for scene in scenes:
        if not isinstance(scene,dict):fail('scene must be an object')
        name=scene.get('id'); kind=scene.get('type')
        if not isinstance(name,str) or not re.fullmatch('[a-z][a-z0-9_]{0,30}',name):fail('invalid scene id')
        if name in names:fail('duplicate scene id')
        names.append(name)
        if kind not in ('platformer','racing'):fail('scene type must be platformer or racing')
        integer(scene,'length',64,8192)
        if kind=='platformer':
            surfaces=scene.get('platforms')
            if not isinstance(surfaces,list) or not 1<=len(surfaces)<=32: fail('platformer needs 1..32 platforms')
            for p in surfaces:
                x=integer(p,'x',0,width-1); y=integer(p,'y',0,height-1)
                w=integer(p,'w',1,width); integer(p,'h',1,height)
                if x+w>width:fail('platform extends past world width')
        if scene.get('next') not in [s.get('id') for s in scenes if isinstance(s,dict)]:
            fail('scene next must name an existing scene')
    if scenes[0]['type']!='platformer' or scenes[1]['type']!='racing':fail('demo supports platformer then racing')
    if scenes[0]['length']>width-16:fail('first platform length exceeds reachable world')
    if world['width']!=512 or world['height']!=224:fail('current generated game assets use a fixed 512x224 world')
    if not any(s['type']=='racing' for s in scenes):fail('a hybrid spec needs a racing segment')
    # Enforce a reachable cycle or path. Each scene has one deterministic successor.
    visited=set(); cursor=scenes[0]['id']; lookup={s['id']:s for s in scenes}
    while cursor not in visited:
        visited.add(cursor);cursor=lookup[cursor]['next']
    if len(visited)!=len(scenes):fail('unreachable scenes from initial scene')
    return data


def generate_header(spec):
    c=spec['controls']; scenes=spec['scenes']
    vals=[('HYBRID_WALK_SPEED_Q8',c['walk_speed_q8']),
          ('HYBRID_GRAVITY_Q8',c['gravity_q8']),
          ('HYBRID_JUMP_Q8',c['jump_velocity_q8']),
          ('HYBRID_RACE_SPEED_Q8',c['race_speed_q8']),
          ('HYBRID_LANE_MIN',c['race_lane_left']),
          ('HYBRID_LANE_MAX',c['race_lane_right']),
          ('HYBRID_FIRST_PLATFORM_LENGTH',scenes[0]['length']),
          ('HYBRID_FIRST_RACE_LENGTH',next(s['length'] for s in scenes if s['type']=='racing'))]
    return ('/* GENERATED by workflows/offline.py generate. Edit the JSON spec, not this file. */\n'
            '#ifndef HYBRID_RULES_H\n#define HYBRID_RULES_H\n'+
            ''.join(f'#define {k} ({v})\n' for k,v in vals)+
            '#endif\n')


def simulate(spec, steps):
    """Integer Q8 deterministic *host oracle*. Does not claim to emulate the PCE ROM."""
    c=spec['controls']; stage=0; scenes=spec['scenes']; x=0; y=0; vy=0; grounded=True
    lane=(c['race_lane_left']+c['race_lane_right'])//2; progress=0; was_jump=False
    frames=[]
    for index,entry in enumerate(steps):
        if not isinstance(entry,dict):fail('scenario step must be object')
        n=entry.get('frames'); buttons=entry.get('buttons')
        if type(n)!=int or not 1<=n<=2000 or not isinstance(buttons,list) or any(b not in ('left','right','up','down','i') for b in buttons):
            fail('invalid scenario frames/buttons')
        for _ in range(n):
            scene=scenes[stage]
            if scene['type']=='platformer':
                dx=(int('right' in buttons)-int('left' in buttons))*c['walk_speed_q8']
                x=max(0,min(scene['length']*256,x+dx))
                jump=('i' in buttons)
                if jump and not was_jump and grounded:
                    vy=c['jump_velocity_q8'];grounded=False
                was_jump=jump
                if not grounded:
                    vy+=c['gravity_q8'];y+=vy
                    if y>=0:y=0;vy=0;grounded=True
                if x>=scene['length']*256:
                    stage=(stage+1)%len(scenes);progress=0
                    lane=(c['race_lane_left']+c['race_lane_right'])//2;x=0;y=0;vy=0;grounded=True
            else:
                lane=max(c['race_lane_left'],min(c['race_lane_right'],lane+2*(int('right' in buttons)-int('left' in buttons))))
                if 'up' in buttons:progress+=c['race_speed_q8']
                if progress>=scene['length']*256:
                    stage=(stage+1)%len(scenes);x=0;y=0;progress=0
            frames.append({'frame':len(frames)+1,'scene':scenes[stage]['id'],
                           'type':scenes[stage]['type'],'x_q8':x,'y_q8':y,
                           'vy_q8':vy,'grounded':grounded,'lane':lane,'race_progress_q8':progress})
    return {'source':'offline physics oracle (not ROM execution)', 'frames':frames,
            'final':frames[-1] if frames else {}}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='cmd',required=True)
    d=sub.add_parser('doctor',help='inspect installed tools; never download')
    d.add_argument('--json',action='store_true')
    q=sub.add_parser('route',help='choose a concrete example from natural-language intent')
    q.add_argument('request',nargs='+')
    brief=sub.add_parser('brief',help='generate a pasteable, offline coding-agent implementation contract')
    brief.add_argument('request',nargs='+');brief.add_argument('--out')
    n=sub.add_parser('new',help='copy a clean, offline working recipe')
    n.add_argument('--recipe',required=True,choices=sorted(RECIPES))
    n.add_argument('--out',required=True)
    v=sub.add_parser('validate',help='validate hybrid game design JSON')
    v.add_argument('spec')
    g=sub.add_parser('generate',help='emit a real C rules header for the hybrid demo')
    g.add_argument('spec');g.add_argument('--out',required=True)
    s=sub.add_parser('simulate',help='simulate integer rules offline, not PCE hardware')
    s.add_argument('spec');s.add_argument('scenario');s.add_argument('--out')
    rom=sub.add_parser('romcheck',help='basic ROM shape check, not emulator verification')
    rom.add_argument('image')
    a=ap.parse_args()
    try:
        if a.cmd=='doctor':
            commands=['mos-pce-clang','mos-pce-cd-clang','make','python3']
            result={'tools':{k:shutil.which(k) for k in commands},
                    'headless_env': bool(os.environ.get('PCE_HEADLESS')),
                    'bios_env':bool(os.environ.get('PCE_SYSTEM_CARD_BIOS')),
                    'checked_without_download':True}
            result['ready_hucard']=all(result['tools'][x] for x in ('mos-pce-clang','make','python3'))
            print(json.dumps(result,indent=2))
        elif a.cmd=='route':
            request=' '.join(a.request)
            print(json.dumps(guidance(choose(request),request),indent=2))
        elif a.cmd=='brief':
            result=agent_brief(' '.join(a.request))
            if a.out:Path(a.out).write_text(result)
            print(result,end='')
        elif a.cmd=='new':
            key=RECIPES[a.recipe]
            micro = a.recipe in ('audio','racer','graphics','sprite','sgx','math')
            src=EXAMPLES / ('micro' if micro else '') / key
            target=Path(a.out).resolve()
            if not src.is_dir():fail(f'missing template: {src}')
            if target.exists():fail('output exists; refusing overwrite')
            if micro:
                # Preserve the documented relative paths (micro/NN -> ../../starter).
                dst=target/'micro'/key
                dst.parent.mkdir(parents=True)
                shutil.copytree(src,dst,ignore=shutil.ignore_patterns('build','__pycache__','screenshot.png'))
                for f in (EXAMPLES/'micro').glob('*.h'):
                    shutil.copy2(f,target/'micro'/f.name)
                shutil.copy2(EXAMPLES/'micro'/'common.mk',target/'micro'/'common.mk')
                shutil.copytree(EXAMPLES/'starter'/'tools',target/'starter'/'tools')
                # Vendored narrow math and strict linker guard; copied micro
                # recipes must build without the original toolkit directory.
                shutil.copytree(EXAMPLES.parent/'libcommon',target/'libcommon',
                                ignore=shutil.ignore_patterns('build','__pycache__'))
                (target/'workflows').mkdir()
                shutil.copy2(Path(__file__).resolve().parent/'arith_guard.py',
                             target/'workflows'/'arith_guard.py')
                shutil.copytree(Path(__file__).resolve().parent/'specs',
                                target/'workflows'/'specs',
                                ignore=shutil.ignore_patterns('__pycache__'))
                build_dir=dst
            else:
                shutil.copytree(src,target,ignore=shutil.ignore_patterns('build','__pycache__','screenshot.png','*.elf','*.mlb','*.map'))
                build_dir=target
            print(json.dumps({'created':str(target),'recipe':key,'build':f'cd {build_dir} && make'},indent=2))
        elif a.cmd=='validate':
            p=parse_spec(a.spec);print(json.dumps({'valid':True,'scenes':[x['id'] for x in p['scenes']]},indent=2))
        elif a.cmd=='generate':
            spec=parse_spec(a.spec); out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(generate_header(spec));print(out)
        elif a.cmd=='simulate':
            spec=parse_spec(a.spec);steps=json.loads(Path(a.scenario).read_text())['steps']
            result=simulate(spec,steps);result['total_frames']=len(result['frames'])
            if a.out:Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps({'total_frames':result['total_frames'],'final':result['final'],'oracle_only':True},indent=2))
        elif a.cmd=='romcheck':
            path=Path(a.image);size=path.stat().st_size
            if size<8192 or size%8192:fail('not a raw bank-aligned HuCard ROM (or not supported by this check)')
            print(json.dumps({'path':str(path),'bytes':size,'bank_aligned':True,'emulator_verified':False},indent=2))
        return 0
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:
        print(f'error: {e}',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
