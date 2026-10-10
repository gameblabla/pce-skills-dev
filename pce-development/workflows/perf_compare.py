#!/usr/bin/env python3
"""Reproducible pre/post LLVM-MOS footprint + instruction-coverage audit.

Coverage counts instructions EXECUTED in the emulator, not HuC6280 cycles.
Idle VBlank polling dominates; never label the result FPS or a cycle benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

def footprint(elf,llvm_size='llvm-size',llvm_nm='llvm-nm'):
    sizes=subprocess.check_output([llvm_size,str(elf)],text=True).splitlines()
    fields=sizes[-1].split()
    if len(fields)<4:raise ValueError('llvm-size output format unexpected')
    nm=subprocess.check_output([llvm_nm,str(elf)],text=True)
    helpers=sorted(set(re.findall(r'\b__(?:[a-z]*mul|[a-z]*div|[a-z]*mod)[a-z0-9_]*\b',nm)))
    return {'bss_bytes':int(fields[2]),'software_math_helpers':helpers,
            'elf_sha256':hashlib.sha256(Path(elf).read_bytes()).hexdigest()}

def coverage(file):
    data=json.loads(Path(file).read_text())
    if data.get('format') not in ('pce-logical-pc-coverage-v1','mednafen-pce-logical-pc-coverage-v1'):
        raise ValueError('unknown instruction-coverage format')
    if data.get('frames',0)<1 or data.get('total_instructions',0)<1:
        raise ValueError('invalid frame or instruction count')
    return {'frames':data['frames'],'instructions':data['total_instructions'],
            'instructions_per_frame':round(data['total_instructions']/data['frames'],2),
            'unique_pcs':data['unique_logical_pcs']}

def compare(before_elf,after_elf,before_cov,after_cov):
    old=footprint(before_elf);new=footprint(after_elf)
    old['coverage']=coverage(before_cov);new['coverage']=coverage(after_cov)
    if old['coverage']['frames']!=new['coverage']['frames']:
        raise ValueError('non-comparable run lengths')
    old_bss=old['bss_bytes'];new_bss=new['bss_bytes']
    old_count=old['coverage']['instructions'];new_count=new['coverage']['instructions']
    return {'baseline':old,'optimized':new,
            'bss_bytes_saved':old_bss-new_bss,
            'bss_reduction_percent':round(100*(old_bss-new_bss)/old_bss,2),
            'emulator_instructions_saved':old_count-new_count,
            'emulator_instruction_reduction_percent':round(100*(old_count-new_count)/old_count,3),
            'limitations':'Emulator PC coverage includes idle polling and gives instruction counts, not per-function cycles or FPS. Hardware measurement required.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for f in ('before-elf','after-elf','before-coverage','after-coverage'):ap.add_argument('--'+f,required=True)
    ap.add_argument('--output')
    a=ap.parse_args()
    try:
        result=compare(a.before_elf,a.after_elf,a.before_coverage,a.after_coverage)
        text=json.dumps(result,indent=2)+'\n'
        if a.output:
            p=Path(a.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        print(text,end='')
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError,ZeroDivisionError) as ex:
        ap.error(str(ex))
if __name__=='__main__':sys.exit(main())
