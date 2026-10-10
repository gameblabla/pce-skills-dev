#!/usr/bin/env python3
"""Measure actual CHANGED raycaster views and BAT words, not idle scans.

A 128x128 BAT redraw counter on the old engine incremented after streaming
unchanged backgrounds. The new counter advances only after *dirty* vertical
column writes. Its number must not be compared to the old full-image pass
counter as equal pixel work. The test also validates screenshots independently.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image
import genre_trace
import platformer_trace

SCENARIO=(('idle',90,()),('turn-right',90,('right',)),
          ('walk',90,('up',)),('turn-left',90,('left',)),
          ('settle',90,()),('quiet',90,()))

def validate(data):
    if len(data)!=len(SCENARIO):raise ValueError('incomplete column benchmark')
    for i,((name,frames,keys),s) in enumerate(zip(SCENARIO,data)):
        if s['segment']!=name or s['emulator_frames']!=frames or tuple(s['buttons'])!=keys:
            raise ValueError('scenario metadata mismatch')
        if not isinstance(s['dirty_views'],int) or not isinstance(s['vram_words'],int):
            raise ValueError('invalid counters')
        if s['dirty_views']<0 or s['vram_words']<0 or s['vram_words']>65535:
            raise ValueError('counter out of range')
        if s['dirty_views'] and not s['vram_words']:
            raise ValueError('fabricated changed view without VRAM writes')
        if s['game_updates']<1:
            raise ValueError('game loop stalled')
        if s['screenshot_colors']<5:
            raise ValueError('unrendered/blank screen')
    if data[0]['dirty_views'] or data[0]['vram_words']:
        raise ValueError('settled idle spurs background redraws')
    # A completed in-flight 32-column pass may contain up to 2*128*32=8192
    # BAT words (two pairs per ray). The old 4096 threshold incorrectly
    # rejected valid close-wall frames after a faster renderer advanced
    # farther during the held-UP segment. The next 90-frame quiet window
    # MUST still show zero writes and zero new changed views.
    if data[-2]['dirty_views']>2 or data[-2]['vram_words']>8192:
        raise ValueError('settling period keeps redrawing excessively')
    if data[-1]['dirty_views'] or data[-1]['vram_words']:
        raise ValueError('fully settled idle still performs VRAM writes')
    if data[1]['dirty_views']<2 or data[3]['dirty_views']<2:
        raise ValueError('rotation failed to render new views')
    if data[1]['vram_words']<200 or data[3]['vram_words']<200:
        raise ValueError('rotation rendered no meaningful wall region')
    return {'passed':True,'changed_views':sum(s['dirty_views'] for s in data),
            'vram_words':sum(s['vram_words'] for s in data),
            'video_frames':sum(s['emulator_frames'] for s in data),
            'turning_views_per_second':round((data[1]['dirty_views']+data[3]['dirty_views'])*60/(SCENARIO[1][1]+SCENARIO[3][1]),3),
            'limitations':['Emulated NTSC seconds, not physical measurements',
                           'A dirty view may update only changed wall spans, unlike a complete framebuffer redraw']}

def run(rom,elf,output):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    rom=Path(rom).resolve();elf=Path(elf).resolve()
    bin=platformer_trace._find_binary(str(rom))
    addr={n:platformer_trace.resolve_trace_address(elf,n) for n in
          ('ray_redraws','ray_bat_words','pce_genre_trace')}
    try:
        addr['ray_codegen_words']=platformer_trace.resolve_trace_address(elf,'ray_codegen_words')
    except RuntimeError:
        pass # Reference ROM deliberately has no generated-code counter.
    client=platformer_trace.NativeControl(str(bin),str(rom),output.parent/(output.stem+'-rpc'),initial_frames=2)
    rows=[]
    try:
        client.call('run',300)
        def sample():
            result={}
            for key in ('ray_redraws','ray_bat_words','ray_codegen_words'):
                if key not in addr:continue
                raw=bytes.fromhex(client.call('memread',hex(addr[key]),2,1)['hex'])
                result[key]=int.from_bytes(raw,'little')
            raw=bytes.fromhex(client.call('memread',hex(addr['pce_genre_trace']),128,1)['hex'])
            result['frame']=genre_trace.choose(raw)['frame']
            return result
        before=sample()
        for name,frames,keys in SCENARIO:
            mask=sum(1<<genre_trace.BUTTONS[b] for b in keys)
            client.call('input',mask)
            client.call('run',frames)
            image=output.parent/(output.stem+'-'+name+'.png')
            image.unlink(missing_ok=True)
            client.call('screenshot',str(image))
            with Image.open(image) as im:colors=len(im.convert('RGB').getcolors(1000000) or [])
            now=sample()
            rows.append({'segment':name,'buttons':list(keys),'emulator_frames':frames,
                         'dirty_views':(now['ray_redraws']-before['ray_redraws'])&65535,
                         'vram_words':(now['ray_bat_words']-before['ray_bat_words'])&65535,
                         'game_updates':(now['frame']-before['frame'])&0xffffffff,
                         'generated_words':(now['ray_codegen_words']-before['ray_codegen_words'])&65535 if 'ray_codegen_words' in addr else None,
                         'screenshot_colors':colors,'screenshot':str(image)})
            before=now
    finally:client.close()
    result=validate(rows)
    doc={'result':'passed','method':'ROM-owned dirty-view and VRAM-word counters + real emulator PNGs',
         'rom':str(rom),'scenario':rows,'totals':result}
    output.write_text(json.dumps(doc,indent=2)+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom',required=True);ap.add_argument('--elf',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args()
    try:
        r=run(args.rom,args.elf,args.output)
        print(json.dumps(r['totals'],indent=2))
    except (OSError,ValueError,RuntimeError) as exc:ap.error(str(exc))
if __name__=='__main__':main()
