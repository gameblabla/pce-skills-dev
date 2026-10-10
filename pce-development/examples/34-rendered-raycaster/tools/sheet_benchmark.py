#!/usr/bin/env python3
"""Native address-setup comparison with the exact same source textures.

Samples ROM-owned completed dirty-view and BAT-upload counters and checks
real emulator screenshots. We don't claim the views are identical work when
one build advances gameplay more often; we report both update rates and words.
"""
import argparse,json
from pathlib import Path
from PIL import Image,ImageChops
import platformer_trace

SCENARIO=(('warm',210,0),('right',180,1<<7),('rest',180,0),
          ('left',180,1<<6),('quiet',210,0))

def run(rom,output):
    rom=Path(rom).resolve();elf=Path(str(rom)+'.elf')
    elf=rom.with_suffix('.pce.elf') if not elf.exists() else elf
    bin=platformer_trace._find_binary(str(rom))
    names=('ray_redraws','ray_bat_words','ray_codegen_words','pce_genre_trace')
    addr={n:platformer_trace.resolve_trace_address(elf,n) for n in names}
    client=platformer_trace.NativeControl(str(bin),str(rom),output.parent/(output.stem+'-rpc'),initial_frames=2)
    data=[]
    try:
        def sample():
            d={}
            for n in names[:3]:
                d[n]=int.from_bytes(bytes.fromhex(client.call('memread',hex(addr[n]),2,1)['hex']),'little')
            # Published frame counter is at +12 in G2TR 64-byte record but
            # use the existing decoder rather than assuming offsets.
            import genre_trace
            raw=bytes.fromhex(client.call('memread',hex(addr['pce_genre_trace']),128,1)['hex'])
            d['update']=genre_trace.choose(raw)['frame'];return d
        client.call('run',300)  # setup uploads all 8,192 BAT entries first
        for segment,frames,mask in SCENARIO:
            client.call('input',mask)
            start=sample();client.call('run',frames);end=sample()
            pic=output.parent/(output.stem+'-'+segment+'.png');pic.unlink(missing_ok=True)
            client.call('screenshot',str(pic))
            im=Image.open(pic).convert('RGB')
            d={n:(end[n]-start[n])&(0xffffffff if n=='update' else 65535) for n in start}
            d.update(name=segment,emulator_frames=frames,colors=len(im.getcolors(1000000) or []),image=str(pic))
            if d['colors']<5:raise ValueError(segment+' screenshot incomplete')
            if d['update']==0:raise ValueError(segment+' game stalled')
            data.append(d)
    finally:client.close()
    if data[0]['ray_bat_words'] or data[-1]['ray_bat_words']:
        raise ValueError('stationary view keeps uploading BAT data')
    if not all(d['ray_codegen_words']>0 for d in data if d['name'] in ('right','left')):
        raise ValueError('generated writer not used')
    return data

def compare(ref,opt):
    if [d['name'] for d in ref]!=[d['name'] for d in opt]:raise ValueError('scenario mismatch')
    return {'segments':[{'name':r['name'], 'legacy_updates':r['update'],
        'native_updates':a['update'], 'legacy_views':r['ray_redraws'],
        'native_views':a['ray_redraws'], 'legacy_words':r['ray_bat_words'],
        'native_words':a['ray_bat_words'], 'native_asm_words':a['ray_codegen_words']}
        for r,a in zip(ref,opt)],
        'legacy_turning_views':ref[1]['ray_redraws']+ref[3]['ray_redraws'],
        'native_turning_views':opt[1]['ray_redraws']+opt[3]['ray_redraws'],
        'video_frames':sum(d['emulator_frames'] for d in ref),
        'limitations':'Same emulator frame/input schedule; different game tick progress and positions. Not fixed-work CPU-cycle evidence.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--optimized',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    o=Path(args.output).resolve();o.parent.mkdir(parents=True,exist_ok=True)
    r=run(args.reference,o.with_name('sheet-legacy'))
    n=run(args.optimized,o.with_name('sheet-native'))
    result=compare(r,n)
    # The stationary camera is initialized identically; compare with a
    # screenshot taken AFTER the warm segment has completed all wall writes.
    a=Image.open(r[0]['image']).convert('RGB');b=Image.open(n[0]['image']).convert('RGB')
    if a.size!=b.size or ImageChops.difference(a,b).getbbox():
        raise ValueError('native/legacy stationary views differ')
    result['stationary_exact_match']=True
    if result['native_turning_views']<result['legacy_turning_views']:
        raise ValueError('native VDC address path regresses turning views')
    result['passed']=True
    o.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError) as e:raise SystemExit(f'sheet FPS FAIL: {e}')
