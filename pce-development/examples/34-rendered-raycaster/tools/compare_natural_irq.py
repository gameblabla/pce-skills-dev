#!/usr/bin/env python3
"""Report equivalent 128x128 IRQ schedules without calling dirty passes FPS."""
import argparse
import json
from pathlib import Path


def compare(standard, natural, visual):
    a=standard['totals']; b=natural['totals']
    if not a['passed'] or not b['passed'] or not visual['matched']:
        raise ValueError('benchmarks and exact settled screenshot must pass')
    if a['video_frames']!=1080 or b['video_frames']!=a['video_frames']:
        raise ValueError('different emulated video frame horizons')
    return {
        'passed': True, 'resolution':[128,128],
        'standard':{'turning_dirty_passes_per_second':a['turning_views_per_second'],
                    'dirty_passes':a['changed_views'], 'bat_words':a['vram_words']},
        'natural':{'turning_dirty_passes_per_second':b['turning_views_per_second'],
                   'dirty_passes':b['changed_views'], 'bat_words':b['vram_words']},
        'raster_events_per_frame':{'standard':127,'natural':68},
        'settled_pixels': {'identical':visual['matched'],
                           'differing':visual['differing_pixels'],
                           'total':visual['pixel_count']},
        'limitations':['Emulator-only measurements; hardware not tested',
                       'Dirty-view passes are not complete atomic video frames',
                       'The 160-word variant is experimental; intermediate budgets failed movement stress',
                       'Input scripts advance a different number of game updates, so camera poses can diverge'],
    }


def main():
    p=argparse.ArgumentParser()
    for option in ('standard','natural','visual','output'):
        p.add_argument('--'+option,required=True)
    a=p.parse_args()
    result=compare(*(json.loads(Path(getattr(a,x)).read_text())
                     for x in ('standard','natural','visual')))
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
