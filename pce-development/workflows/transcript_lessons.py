#!/usr/bin/env python3
"""Extract only aggregate failure/goal categories from exported sessions offline.

Does not print personal text, file paths, prompts, embedded tool output, or raw conversations.
Only pass archives you are allowed to process. Transcripts are not training material.
"""
import argparse
import collections
import json
import re
import zipfile

CATEGORIES={
 'platformer_collision':r'platformer|collision|grounded|landing|jump|wall',
 'racing_camera':r'mode.?7|racing|road|backwards|camera|scroll',
 'sprite_sat':r'sprite|satb|animation|cull|priority',
 'audio_isolation':r'psg|voice sample|sound|adpcm|dda',
 'banking_memory':r'bank full|bank overflow|mpr|bank relocation|arcade card|vram|ram',
 'headless_verification':r'headless|emulator|screenshot|trace|P2TR|profil|regression',
 'toolchain_cd':r'llvm.mos|bios|cd.rom|ipl|makefile|toolchain',
 'release_evidence':r'git commit|build|60 fps|performance|test',
}

def summarize(path):
    counts=collections.Counter();files=0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(('.md','.txt')):continue
            # Keep sessions bounded. Repeated generated outputs should not dominate.
            if info.file_size>32*1024*1024:continue
            text=archive.read(info).decode('utf8','replace')
            files+=1
            for category,pattern in CATEGORIES.items():
                if re.search(pattern,text,re.I):counts[category]+=1
    return {'sessions_scanned':files,'category_session_presence':dict(sorted(counts.items())),
            'raw_conversations_in_output':False,
            'warning':'counts indicate presence, not severity or correctness'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('zip');p.add_argument('--output');args=p.parse_args()
    result=json.dumps(summarize(args.zip),indent=2)+'\n'
    if args.output:open(args.output,'w',encoding='utf8').write(result)
    print(result,end='')
