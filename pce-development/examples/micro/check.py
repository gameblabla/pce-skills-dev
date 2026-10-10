#!/usr/bin/env python3
"""Build every micro example and statically enforce audio/video separation."""
import pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent
projects = sorted(p for p in root.iterdir() if p.is_dir() and (p / "Makefile").exists())
failed=[]
for p in projects:
    src=(p/'main.c').read_text()
    if 'psg-' in p.name:
        bad=[token for token in ('pce_vdc','pce_vce','IO_VDC','IO_VCE','demo_video','draw_text','graphics_init','gfx.h') if token in src]
        if bad: failed.append(f'{p.name}: audio/video mixing {bad}')
    build=subprocess.run(['make','-s','--no-print-directory'], cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    print(('OK ' if build.returncode==0 else 'FAIL ')+p.name)
    if build.returncode: failed.append(f'{p.name}: {build.stdout[-1400:]}')
print(f'{len(projects)-len(failed)}/{len(projects)} builds passed')
if failed:
    print('\n'.join(failed),file=sys.stderr);sys.exit(1)
