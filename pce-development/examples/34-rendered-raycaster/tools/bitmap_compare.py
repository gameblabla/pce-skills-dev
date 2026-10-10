#!/usr/bin/env python3
"""Same-scenario *completed bitmap pass* comparison; measured, not estimated."""
import argparse
import json
from pathlib import Path


def compare(before,after):
    if before.get('result')!='passed' or after.get('result')!='passed':
        raise ValueError('both bitmap runs must pass screenshots and progress checks')
    if before.get('format')!='paired-bat-completed-pass-v1' or after.get('format')!=before['format']:
        raise ValueError('invalid bitmap report format')
    if before.get('logical_pixels')!=after.get('logical_pixels') or not before.get('logical_pixels'):
        raise ValueError('bitmap geometries differ or are missing; redraw counts are not equivalent pixel work')
    bs,ns=before['segments'],after['segments']
    if len(bs)!=len(ns) or any((a['segment'],a['buttons'],a['emulator_frames']) !=
                               (b['segment'],b['buttons'],b['emulator_frames'])
                               for a,b in zip(bs,ns)):
        raise ValueError('benchmark scenarios differ; no valid speed comparison')
    a=before['totals'];b=after['totals']
    if a['emulator_frames']!=b['emulator_frames'] or not a['completed_redraws'] or not b['completed_redraws']:
        raise ValueError('invalid completed redraw counters')
    advantage=(b['completed_redraws']-a['completed_redraws'])*100/a['completed_redraws']
    return {'result':'passed' if advantage>0 else 'regression',
            'baseline_completed_redraws':a['completed_redraws'],
            'optimized_completed_redraws':b['completed_redraws'],
            'baseline_updates':a['game_updates'],
            'optimized_updates':b['game_updates'],
            'emulator_frames':a['emulator_frames'],
            'completed_redraw_improvement_pct':round(advantage,2),
            'measurement':'actual VDC BAT passes completed per equal-length input scenario; NOT game loop FPS',
            'note':'Different update counts and pixel work; no per-routine same-work speedup is claimed'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True,type=Path)
    p.add_argument('--optimized',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    try:
        report=compare(json.loads(a.baseline.read_text()),json.loads(a.optimized.read_text()))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        if report['result']!='passed':p.exit(1,'Redraw throughput regression\n')
    except (ValueError,OSError) as exc:p.error(str(exc))
if __name__=='__main__':main()
