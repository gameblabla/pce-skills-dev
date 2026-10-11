#!/usr/bin/env python3
"""Six-segment movement/turning smoke test for the lossy tiled page-flip path."""
import argparse,json
from pathlib import Path
from PIL import Image
import genre_trace,platformer_trace
STEPS=((180,()),(180,('right',)),(180,('right',)),(180,('up',)),(180,('left',)),(180,()))
def run(rom,elf,output):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    addr=platformer_trace.resolve_trace_address(elf,'ray_redraws')
    trace=platformer_trace.resolve_trace_address(elf,'pce_genre_trace')
    app=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(app),str(Path(rom).resolve()),output.parent/(output.stem+'-rpc'),initial_frames=2)
    prev_updates=0;prev_flips=0;hashes=set();report=[]
    try:
        for index,(frames,keys) in enumerate(STEPS):
            buttons=sum(1<<genre_trace.BUTTONS[k] for k in keys)
            client.call('input',buttons);client.call('run',frames)
            picture=output.parent/(output.stem+f'-{index}.png')
            picture.unlink(missing_ok=True);client.call('screenshot',str(picture))
            im=Image.open(picture).convert('RGB')
            if im.size!=(560,242):raise ValueError('wrong tiled pageflip resolution')
            colors=len(im.getcolors(200000) or [])
            if colors<6:raise ValueError(f'blank or incorrect image in segment {index}: {colors} colors')
            hashes.add(im.crop((24,16,536,240)).tobytes())
            n=int.from_bytes(bytes.fromhex(client.call('memread',hex(addr),2,1)['hex']),'little')
            data=bytes.fromhex(client.call('memread',hex(trace),128,1)['hex'])
            traced=genre_trace.choose(data)
            updates=traced['frame']
            if index and (updates<=prev_updates or n<=prev_flips):
                raise ValueError(f'view/gameplay stalled in segment {index}')
            if (traced['buttons']&255)!=buttons:raise ValueError('input was not acknowledged')
            report.append({'segment':index,'buttons':keys,'complete_vblank_flips':n,'game_updates':updates,'screenshot_colors':colors})
            prev_updates,prev_flips=updates,n
    finally:client.close()
    if len(hashes)<3:raise ValueError('camera scenes do not change under input')
    result={'passed':True,'emulator_frames':1080,'scene_variations':len(hashes),'segments':report,
            'note':'Lossy 2-color tile presenter; screenshots are emulator evidence, not hardware timing proof'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--elf',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    try:run(a.rom,a.elf,a.output)
    except (ValueError,RuntimeError,OSError) as e:p.error(str(e))
