#!/usr/bin/env python3
"""Run offline paired HuCard instruction-coverage/footprint tests.

`--baseline` must point to a LOCAL checkout. No git fetch, build download,
or emulator configuration is performed on behalf of the user.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from perf_compare import compare

PROJECTS=('26-platformer-starter','27-platformer-racer')

def run_pair(baseline,current,emulator,destination,frames=240):
    for p in (baseline,current):
        if not (p/'pce-development/examples/26-platformer-starter/Makefile').is_file():
            raise ValueError(f'not a toolkit checkout: {p}')
    if not emulator.is_file():raise ValueError('headless emulator executable missing')
    if not 30<=frames<=3600:raise ValueError('frames must be within 30..3600')
    destination.mkdir(parents=True,exist_ok=True)
    results={}
    for project in PROJECTS:
        files={}
        for label,source in (('baseline',baseline),('optimized',current)):
            folder=source/'pce-development/examples'/project
            subprocess.run(['make','--no-print-directory','-C',str(folder)],check=True,
                           stdout=subprocess.DEVNULL)
            elf=folder/'build'/f'{project}.pce.elf'
            rom=folder/'build'/f'{project}.pce'
            cov=destination/f'{label}-{project}-coverage.json'
            cov.unlink(missing_ok=True)
            runbase=destination/f'{label}-{project}-emustate'
            runbase.mkdir(exist_ok=True)
            subprocess.run([str(emulator),'--rom',str(rom),'--frames',str(frames),
                            '--base-dir',str(runbase),'--cov',str(cov)],check=True,
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            files[label]=(elf,cov)
        result=compare(files['baseline'][0],files['optimized'][0],files['baseline'][1],files['optimized'][1])
        results[project]=result
    (destination/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True,type=Path)
    p.add_argument('--current',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--emulator',required=True,type=Path)
    p.add_argument('--out',type=Path,default=Path('build/platformer-perf'))
    p.add_argument('--frames',type=int,default=240)
    a=p.parse_args()
    try:
        result=run_pair(a.baseline.resolve(),a.current.resolve(),a.emulator.resolve(),a.out.resolve(),a.frames)
        print(json.dumps({project:{'bss_saved':v['bss_bytes_saved'],
             'instruction_count_change':v['emulator_instructions_saved']}
             for project,v in result.items()},indent=2))
        print('Full audit:',(a.out/'comparison.json').resolve())
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        p.error(str(e))
if __name__=='__main__':sys.exit(main())
