#!/usr/bin/env python3
"""Static invariants for the training demos; no emulation or gameplay claims."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def check():
    failures=[]
    game=ROOT/'examples/27-platformer-racer/src/main.c'
    if not game.exists():return ['missing hybrid source']
    text=game.read_text()
    required={'world physics':'player_sprite_x_q8','gravity':'GRAVITY_Q8',
              'crossing-based landing':'previous_feet <= top && proposed_feet >= top',
              'camera separate':'player_sprite_x_q8 >> 8) - (camera_x_q8 >> 8)',
              'race X':'hybrid_race_lane_q8','race Y':'hybrid_race_progress_q8',
              'transition':'hybrid_enter_platformer();','telemetry':'publish_trace(',
              'Q8 rules':'hybrid_rules.h'}
    for name,token in required.items():
        if token not in text:failures.append(f'missing {name}: {token}')
    for project in ('26-platformer-starter','27-platformer-racer'):
        p=ROOT/'examples'/project
        if not (p/'Makefile').exists():failures.append(f'{project} missing Makefile')
        if any(sub.exists() for sub in (p/'src'/'sound.c',p/'src'/'psg.c')):
            failures.append(f'{project} has unrelated audio code')
    return failures

if __name__=='__main__':
    a=argparse.ArgumentParser();a.parse_args()
    problems=check();print(json.dumps({'passed':not problems,'problems':problems},indent=2));raise SystemExit(bool(problems))
