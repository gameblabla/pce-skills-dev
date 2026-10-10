#!/usr/bin/env python3
"""Compare two DIFFERENT paired-BAT presentation tradeoffs without false FPS claims."""
import argparse
import json
from pathlib import Path


def compare(full,atomic):
    if any(r.get('result')!='passed' for r in (full,atomic)):
        raise ValueError('both reports need independent screenshot validation')
    if (full.get('render_mode'),atomic.get('render_mode'))!=('full','atomic'):
        raise ValueError('need one 128x128 full report and one 128x64 atomic report')
    if full.get('logical_pixels')!=[128,128] or atomic.get('logical_pixels')!=[128,64]:
        raise ValueError('incorrect declared image geometry')
    if [(x['buttons'],x['emulator_frames']) for x in full['segments']] != [
            (x['buttons'],x['emulator_frames']) for x in atomic['segments']]:
        raise ValueError('input scenarios differ')
    a,b=full['totals'],atomic['totals']
    if a['emulator_frames']!=b['emulator_frames'] or a['emulator_frames']<1:
        raise ValueError('unequal emulator duration')
    if min(a['completed_redraws'],b['completed_redraws'])<1:
        raise ValueError('incomplete image passes')
    fpx=a['completed_redraws']*128*128
    apx=b['completed_redraws']*128*64
    return {'result':'passed','emulator_frames':a['emulator_frames'],
        'full_resolution':{'logical_pixels':[128,128],'presentation':'progressive',
                           'finished_passes':a['completed_redraws'],'logical_pixels_processed':fpx,
                           'game_updates':a['game_updates']},
        'atomic_half_height':{'logical_pixels':[128,64],'presentation':'VBlank-swapped',
                           'finished_passes':b['completed_redraws'],'logical_pixels_processed':apx,
                           'game_updates':b['game_updates']},
        'relative_completed_pixel_work_pct':round(100*apx/fpx,2),
        'interpretation':'Count of atomic 128x64 swaps may be ~2x while completed logical pixel work stays similar; not equivalent image quality or FPS',
        'limitations':['Emulator measurements, not hardware timing','No full-resolution 128x128 double buffering inside the BAT','Pixel work excludes fixed ray setup and texture lookup costs']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',type=Path,required=True)
    p.add_argument('--atomic',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        result=compare(json.loads(a.full.read_text()),json.loads(a.atomic.read_text()))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
if __name__=='__main__':main()
