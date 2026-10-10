#!/usr/bin/env python3
"""Offline source and linked-ELF arithmetic gate for 8/16-bit HuC6280 code.

New sources cannot introduce 32/64-bit C operations. Existing frozen ABI/
legacy lines are explicitly enumerated in specs/arith-legacy.json and must be
reviewed if changed. Only static C/ASM is scanned; host Python tooling is not
running on HuC6280 and may use native widths.
"""
import argparse
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter

BASE=Path(__file__).resolve().parents[1]
MANIFEST=Path(__file__).resolve().parent/'specs/arith-legacy.json'
BAD_WIDTH=re.compile(r"\b(?:u?int(?:32|64)_t|(?:u?int)_(?:fast|least)(?:32|64)_t|(?:unsigned\s+)?long(?:\s+long)?|double|float|_Float\d+|__int128)\b|\b(?:0[xX][a-fA-F0-9]+|[0-9]+)(?:ULL|LLU|UL|LU|LL|L)\b",re.I)
SOFT_MATH=re.compile(r"^__(?:u?mul|u?div|u?mod|(?:mul|div|mod|add|sub|fix|float|trunc|extend)[a-z]*)(?:qi|hi|si|di|sf|df|tf|3|4)(?:[0-9]*)$",re.I)
MATH_STEMS=('__mul','__umul','__div','__udiv','__mod','__umod',
            '__muls','__divs','__floats','__fix','__addsf','__subsf',
            '__mulsf','__divsf','__adddf','__subdf','__muldf','__divdf')
LIBM_FUNCS={'sin','cos','tan','atan','atan2','sqrt','pow','log','exp','floor','ceil',
            'sinf','cosf','sqrtf','powf','fmod','fmodf','ldexp','frexp'}

def clean_c(data):
    # Keep line breaks and substitute spaces, so errors retain useful line numbers.
    regex=r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(regex,lambda match:''.join('\n' if c=='\n' else ' ' for c in match.group()),data)

def forbidden_lines(source):
    text=clean_c(source)
    out=[]
    for n,line in enumerate(text.splitlines(),1):
        if BAD_WIDTH.search(line):
            out.append((n,line.strip()))
    return out

def line_hash(line):return hashlib.sha256(line.encode()).hexdigest()[:16]

def load_legacy(path=MANIFEST):
    return json.loads(Path(path).read_text()).get('exceptions',{})

def scan(root,manifest=MANIFEST):
    base=Path(root).resolve(); legacy=load_legacy(manifest)
    failures=[]; allowed=[]; files=0
    for file in sorted(base.rglob('*')):
        if file.suffix not in ('.c','.h') or 'build' in file.parts or '__pycache__' in file.parts:continue
        files+=1
        try:rel=str(file.relative_to(BASE.resolve()))
        except ValueError:rel=str(file.relative_to(base))
        permit=legacy.get(rel,{})
        approved=permit.get('line_hash_counts',{})
        seen=Counter()
        for number,line in forbidden_lines(file.read_text(errors='replace')):
            record={'file':rel,'line':number,'source':line[:140],'code':'wide-arithmetic','hash':line_hash(line)}
            if seen[record['hash']] < approved.get(record['hash'],0):allowed.append(record)
            else:failures.append(record)
            seen[record['hash']]+=1
    for make in sorted(base.rglob('Makefile')):
        if 'build' in make.parts:continue
        for number,line in enumerate(make.read_text(errors='replace').splitlines(),1):
            code=line.split('#',1)[0]
            if re.search(r'(?<!\S)-(?:lm|lgcc)(?!\S)|(?:/|\b)lib(?:m|gcc)\.a\b',code):
                failures.append({'code':'forbidden-link-math','file':str(make),'line':number,
                                 'source':code.strip(),'fix':'use libcommon or a narrow precomputed lookup'})
    return {'ok':not failures,'files':files,'legacy_lines':len(allowed),'issues':failures}

def elf_scan(elf,nm='llvm-nm'):
    result=subprocess.run([nm,str(elf)],capture_output=True,text=True)
    if result.returncode:raise ValueError('llvm-nm failed: '+result.stderr[-500:])
    found=[]
    for row in result.stdout.splitlines():
        bits=row.strip().split()
        if len(bits)<2:continue
        symbol=bits[-1];lower=symbol.lower()
        if lower in LIBM_FUNCS or any(lower.startswith(stem) for stem in MATH_STEMS):
            found.append(symbol)
    return {'ok':not found,'elf':str(elf),'software_math':sorted(set(found))}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='action',required=True)
    a=sub.add_parser('source');a.add_argument('path',nargs='?',default=str(BASE/'examples'))
    a.add_argument('--manifest',default=str(MANIFEST))
    a=sub.add_parser('elf');a.add_argument('file');a.add_argument('--nm',default='llvm-nm')
    a=sub.add_parser('audit');a.add_argument('path');a.add_argument('--min-roms',type=int,default=1)
    a=sub.add_parser('baseline-report');a.add_argument('path',nargs='?',default=str(BASE/'examples'))
    args=ap.parse_args()
    try:
        if args.action=='elf':report=elf_scan(args.file,args.nm)
        elif args.action=='audit':
            elfs=sorted(Path(args.path).glob('*/build/*.pce.elf'))
            bad=[elf_scan(x) for x in elfs]
            bad=[x for x in bad if not x['ok']]
            report={'ok':not bad and len(elfs)>=args.min_roms,
                    'checked_roms':len(elfs),'minimum':args.min_roms,
                    'offenders':bad}
        else:report=scan(args.path)
        print(json.dumps(report,indent=2))
        return 0 if report['ok'] or args.action=='baseline-report' else 1
    except (ValueError,OSError) as e:
        print(str(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
