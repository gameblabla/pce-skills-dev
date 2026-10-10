#!/usr/bin/env python3
"""No-network static SDK/API guard, compiler log triage and honest evidence gate.

Designed from recurring failure cases in local coding-agent transcripts.
It does NOT substitute for compilation, headless execution or hardware testing.
"""
import argparse
import difflib
import json
from pathlib import Path
import re
import sys
import shutil
import os
import hashlib

# This small allowlist is intentionally NOT a replacement for the installed SDK.
# It catches the most common hallucinations even when the SDK is unavailable.
SDK_NAMES = {
    'KEY_1', 'KEY_2', 'KEY_RUN', 'KEY_SELECT', 'KEY_UP', 'KEY_DOWN',
    'KEY_LEFT', 'KEY_RIGHT', 'VDC_SPRITE_FLIP_X', 'VDC_SPRITE_FLIP_Y',
    'VDC_SPRITE_FG', 'VDC_SPRITE_COLOR', 'VCE_PIXEL_CLOCK_5MHZ',
    'VDC_FLAG_VBLANK', 'VDC_FLAG_SCANLINE',
}
INVALID = {
    'KEY_A': 'KEY_1 (PC Engine button I)',
    'KEY_B': 'KEY_2 (PC Engine button II)',
    'KEY_START': 'KEY_RUN',
    'KEY_I': 'KEY_1',
    'KEY_II': 'KEY_2',
    'VDC_SPRITE_HFLIP': 'VDC_SPRITE_FLIP_X',
    'VDC_SPRITE_VFLIP': 'VDC_SPRITE_FLIP_Y',
}
# Categories correspond to failures observed in the user-supplied sessions.
DIAGNOSES = [
    ('sdk-key', r"(?:undeclared identifier ['\"](?:KEY_A|KEY_B|KEY_START|KEY_I|KEY_II)|['\"]KEY_(?:UP|DOWN|LEFT|RIGHT)['\"] macro redefined)",
     'Use pce/joypad.h symbols; do not redefine KEY_* or use SNES buttons. Try model_guard.py scan.'),
    ('sdk-sprite', r"undeclared identifier ['\"]VDC_SPRITE_(?:HFLIP|VFLIP)['\"]",
     'Use VDC_SPRITE_FLIP_X/Y from the installed SDK; check the headers.'),
    ('array-count', r'excess elements in array initializer',
     'Generate arrays from structured data with assetpack.py; never hand-count 128 columns.'),
    ('rom-overflow', r'(?:will not fit in region|overflowed by \d+ bytes|unable to move location counter|file range overlaps with .vector)',
     'Stop: inspect the linker map and scripts/bank_space.py. Do not reduce the level length or silently move overlays.'),
    ('unused-werror', r'(?:unused variable|unused-but-set|[-]Werror,[-]Wunused)',
     'Either implement the feature using the variable or remove unused code; do not drop -Werror to hide faults.'),
    ('rpc-unsupported', r'(?:unknown rpc command|unsupported rpc|unknown command.*(?:input|trace_frames|memread))',
     'Headless binary lacks required RPC commands. Use the bundled RPC-capable source and make trace / make hybrid-test; do not claim a trace.'),
    ('cd-image', r'(?:no disc image|not a bootable cd|cd.*(?:iso|cue).*(?:missing|not found))',
     'A HuCard .pce and linked .bin are not a Super CD-ROM2 image; IPL and user BIOS/disc packager are required.'),
    ('emulator-timeout', r'(?:exit code 124|command timed out|timeout: failed to run command|lockfile issue)',
     'A GUI timeout/lockfile is not game validation. Use make run/debug with PCE_HEADLESS and new base directory.'),
    ('generated-missing', r'(?:demo_assets\.h|level_data\.c|assets\.h).*?(?:No such file|not found)',
     'Run the asset generator first and declare generated headers as Makefile prerequisites.'),
]

def hide_comments(text):
    """Drop comments and quoted strings, retain newlines for source locations."""
    rx=r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(rx, lambda m: '\n'*m.group(0).count('\n') + ' ', text)

def scan(project):
    base=Path(project)
    if not base.is_dir(): raise ValueError(f'not a project folder: {base}')
    src=base/'src' if (base/'src').is_dir() else base
    diagnostics=[]
    files=sorted(set(src.rglob('*.c')) | set(src.rglob('*.h')))
    for f in files:
        if 'build' in f.parts or '__pycache__' in f.parts:continue
        raw=f.read_text(encoding='utf-8',errors='replace')
        clean=hide_comments(raw)
        for sym,replacement in INVALID.items():
            for match in re.finditer(r'\b'+sym+r'\b',clean):
                line=clean.count('\n',0,match.start())+1
                diagnostics.append({'code':'invalid-sdk-symbol','file':str(f.relative_to(base)),
                                    'line':line,'symbol':sym,'fix':f'use {replacement}'})
        for match in re.finditer(r'^\s*#\s*define\s+(KEY_(?:UP|DOWN|LEFT|RIGHT|1|2|RUN|SELECT))\b',clean,re.M):
            diagnostics.append({'code':'redefined-joypad','file':str(f.relative_to(base)),
                                'line':clean.count('\n',0,match.start())+1,
                                'symbol':match.group(1),'fix':'include <pce.h> and use existing joypad.h constants'})
        # Only exempt the exact byte-for-byte generated VN C asset when its
        # manifest names real source PNG hashes. Never exempt arbitrary files
        # merely for containing a GENERATE comment: local AI can invent those.
        verified_generated=False
        manifest=base/'src/manifest.json'
        if f.name=='vn_assets.c' and f.parent==base/'src' and manifest.is_file():
            try:
                meta=json.loads(manifest.read_text())
                sources=meta['source_hashes']
                verified_generated=(meta.get('format')=='pce-vn-pack-v1' and
                    meta.get('generated_c_sha256')==hashlib.sha256(f.read_bytes()).hexdigest() and
                    all(name in ('background.png','mouth_closed.png','mouth_open.png') and
                        hashlib.sha256((base/'assets'/name).read_bytes()).hexdigest()==digest
                        for name,digest in sources.items()) and len(sources)==3)
            except (ValueError,KeyError,OSError,TypeError):pass
        # Generic arrays of per-pixel literal data in C tend to swamp the linker.
        if not verified_generated and f.suffix=='.c' and len(raw)>48000 and len(re.findall(r'0x[\da-fA-F]{2}|\b\d+\s*,',clean))>4000:
            diagnostics.append({'code':'large-inline-assets','file':str(f.relative_to(base)),
                                'line':1,'fix':'pack with assetpack.py; inspect ROM bank budget before building'})
    return diagnostics

def diagnose(text):
    hits=[]
    for code,pat,fix in DIAGNOSES:
        match=re.search(pat,text,re.I)
        if match: hits.append({'code':code,'example':match.group(0)[:120],'action':fix})
    if not hits:
        hits=[{'code':'unclassified','action':'Preserve the complete compiler/emulator log. Check failing command, target, linker map, and SDK headers.'}]
    return hits

LEVELS=('compiled','neutral_emulator','input_scenario','visual_review','real_cd_boot','hardware')

def evidence(manifest):
    m=json.loads(Path(manifest).read_text())
    if not isinstance(m,dict) or m.get('target') not in ('hucard','supercd','supergrafx'):
        raise ValueError('evidence target must be hucard, supercd or supergrafx')
    stages=m.get('evidence')
    if not isinstance(stages,dict): raise ValueError('evidence must be an object')
    for name,value in stages.items():
        if name not in LEVELS or type(value) is not bool:raise ValueError(f'invalid boolean evidence: {name}')
    # Declaration of checked evidence is not independently audited here. Claims of completion
    # are gated by distinct checks, and missing data always fails closed.
    required=['compiled','neutral_emulator','input_scenario','visual_review']
    if m['target']=='supercd':required+=['real_cd_boot']
    if m.get('claim_hardware'):required+=['hardware']
    missing=[x for x in required if stages.get(x) is not True]
    if m['target']=='supercd' and str(m.get('artifact','')).lower().endswith(('.pce','.bin')):
        missing.append('packaged CD disc image (not raw .pce/.bin)')
    report={'target':m['target'],'artifact':m.get('artifact',''),
            'required':required,'missing':missing, 'complete':not missing,
            'warning':'Boolean claims are self-reported; attach reproducible logs, scene captures, and input traces.'}
    return report

def installed_sdk_declarations(name, include_dir=None):
    """Search real local LLVM-MOS PCE headers, never guess SDK APIs."""
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name):
        raise ValueError('expected one C identifier')
    if include_dir is None:
        compiler=shutil.which('mos-pce-clang')
        if not compiler:return []
        include_dir=Path(compiler).resolve().parent.parent/'mos-platform/pce-common/include'
    include_dir=Path(include_dir)
    if not include_dir.exists():return []
    hits=[]
    for f in sorted(include_dir.rglob('*.h')):
        if len(hits)>=12:break
        for i,line in enumerate(f.read_text(errors='replace').splitlines(),1):
            if re.search(r'\b'+re.escape(name)+r'\b',line):
                hits.append({'header':str(f.relative_to(include_dir)),'line':i,'declaration':line.strip()[:220]})
                if len(hits)>=12:break
    return hits

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('scan');s.add_argument('project',nargs='?',default='.')
    d=sub.add_parser('diagnose');d.add_argument('log',help='build/emulator log file or - for stdin')
    e=sub.add_parser('evidence');e.add_argument('manifest')
    k=sub.add_parser('symbol');k.add_argument('name');k.add_argument('--include-dir',default=None)
    a=p.parse_args()
    try:
        if a.command=='scan':
            findings=scan(a.project);out={'ok':not findings,'scanned':a.project,'findings':findings}
        elif a.command=='diagnose':out={'diagnoses':diagnose(sys.stdin.read() if a.log=='-' else Path(a.log).read_text(errors='replace'))}
        elif a.command=='evidence':out=evidence(a.manifest)
        else:
            n=a.name;declarations=installed_sdk_declarations(n,a.include_dir)
            out={'symbol':n,'known_valid':n in SDK_NAMES or bool(declarations),
                 'sdk_declarations':declarations,
                 'suggestion':INVALID.get(n) or difflib.get_close_matches(n,sorted(SDK_NAMES),n=3),
                 'note':'Actual installed SDK header matches are authoritative; the allowlist is only a fallback.'}
        print(json.dumps(out,indent=2));return int(a.command=='scan' and not out['ok'] or a.command=='evidence' and not out['complete'])
    except (OSError,ValueError,json.JSONDecodeError) as err:
        print(f'error: {err}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
