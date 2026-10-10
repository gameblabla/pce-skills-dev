#!/usr/bin/env python3
"""Source-shape checks for Q4 platformer/hybrid training demos (offline only).

Do not anchor validation to stale variable names or obsolete P2TR ABI strings.
Compiler and emulator acceptance remain required separately.
"""
import argparse
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def check():
    failures=[]
    base=ROOT/'examples'
    for project in ('26-platformer-starter','27-platformer-racer'):
        folder=base/project
        files=['src/main.c','src/platformer_q4.h','tools/p4tr.h','tools/p4_trace.py']
        for file in files:
            if not (folder/file).is_file():failures.append(f'{project} missing {file}')
        if any(not (folder/file).is_file() for file in files):continue
        code=(folder/'src/main.c').read_text()
        physics=(folder/'src/platformer_q4.h').read_text()
        trace=(folder/'tools/p4tr.h').read_text()
        checks={'world movement': 'p4_tick(&player,pad,&events)',
                'camera independent': 'player.x-player.camera',
                'trace publication': 'p4_publish(',
                'frame cadence': 'demo_wait_frame()',
                'no sound': 'demo_video_init('}
        for label,token in checks.items():
            if token not in code:failures.append(f'{project}: missing {label}')
        for token in ('p4_supported','p4_overlaps','old_feet<=top','new_feet>=top',
                      'P4_GRAVITY','P4_JUMP','P4_TERMINAL','p4->'):
            if token=='p4->':continue
            if token not in physics:failures.append(f'{project}: missing physics {token}')
        if 'sizeof(P4Trace)==32' not in trace:failures.append(f'{project}: incorrect trace record size')
        if re.search(r'\b(?:u?int(?:32|64)_t|long|float|double)\b',code+physics+trace):
            failures.append(f'{project}: forbidden wide runtime type')
        if any((folder/'src'/name).exists() for name in ('sound.c','psg.c')):
            failures.append(f'{project}: unrelated sound code')
    hybrid=(base/'27-platformer-racer/src/main.c').read_text()
    for token in ('hybrid_scene','hybrid_race_lane_px','hybrid_race_progress_px',
                  'enter_race()','enter_platformer()','demo_restore_platform_background'):
        if token not in hybrid:failures.append(f'hybrid missing {token}')
    video=(base/'27-platformer-racer/src/demo_video.c').read_text()
    if 'pce_vdc_poke(VDC_REG_VRAM_DATA,sprite.attr)' not in video:
        failures.append('hybrid: SAT writes must use nonblocking direct VDC words')
    return failures

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    problems=check()
    print(json.dumps({'passed':not problems,'problems':problems},indent=2))
    raise SystemExit(bool(problems))
