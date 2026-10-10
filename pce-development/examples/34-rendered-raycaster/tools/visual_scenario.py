#!/usr/bin/env python3
"""Independent input-driven G2TR + screenshot acceptance test (offline RPC).

Unlike game-authored traces, these PNGs come from the emulator's rendered
framebuffer. Compare two screenshots, require visible differences inside a
user-defined ROI, and optionally cross-check actor X motion with G2TR data.
Never turn a static screenshot or state-only probe into 'gameplay verified'.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops
import genre_trace
import platformer_trace


def check_pngs(before, after, require):
    with Image.open(before) as a, Image.open(after) as b:
        a=a.convert('RGB');b=b.convert('RGB')
        if a.size!=b.size:raise ValueError('captured image sizes differ')
        colors=len(set(a.get_flattened_data()) | set(b.get_flattened_data()))
        if colors<require.get('min_colors',2):
            raise ValueError(f'only {colors} visible colours; expected at least {require.get("min_colors",2)}')
        diff=ImageChops.difference(a,b)
        changed=sum(any(pixel) for pixel in diff.get_flattened_data())
        if changed<require.get('min_changed_pixels',1):
            raise ValueError(f'only {changed} screenshot pixels changed; expected movement')
        region=require.get('changed_region')
        region_changed=None
        if region:
            if len(region)!=4 or not (0<=region[0]<region[2]<=a.width and 0<=region[1]<region[3]<=a.height):
                raise ValueError('invalid changed_region bounds')
            sub=diff.crop(tuple(region))
            region_changed=sum(any(pixel) for pixel in sub.get_flattened_data())
            if region_changed<require.get('min_region_changed_pixels',1):
                raise ValueError(f'only {region_changed} pixels changed inside the gameplay region')
        return {'size':list(a.size),'colors':colors,'changed_pixels':changed,
                'changed_region':region,'region_changed_pixels':region_changed,
                'bounding_box':list(diff.getbbox() or ())}


def run(rom, scenario, output, elf=None):
    scenario=json.loads(Path(scenario).read_text())
    steps=scenario.get('steps')
    if not isinstance(steps,list) or not 2<=len(steps)<=12:
        raise ValueError('visual scenario needs 2..12 steps')
    expected_genre=scenario.get('genre')
    if expected_genre not in genre_trace.GENRES.values():raise ValueError('unknown genre')
    for step in steps:
        if not 1<=step.get('frames',0)<=360 or any(k not in genre_trace.BUTTONS or genre_trace.BUTTONS[k]>7 for k in step.get('buttons',[])):
            raise ValueError('invalid screenshot scenario steps')
    if sum(step['frames'] for step in steps)>1200:raise ValueError('scenario too long')
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    addr=platformer_trace.resolve_trace_address(elf or str(rom)+'.elf','pce_genre_trace')
    if addr>0xffff and addr>>16==0xF8:addr &=0xffff
    exe=platformer_trace._find_binary(str(rom))
    client=platformer_trace.NativeControl(str(exe),str(Path(rom).resolve()),out.parent/'visual-rpc',initial_frames=2)
    captures=[]
    try:
        for index,step in enumerate(steps):
            mask=sum(1<<genre_trace.BUTTONS[key] for key in step.get('buttons',[]))
            client.call('input',mask)
            client.call('run',step['frames'])
            if step.get('capture',True):
                path=out.parent/(out.stem+f'-{index}.png')
                if path.exists():path.unlink() # local test's own prior capture only
                client.call('screenshot',str(path))
                pair=bytes.fromhex(client.call('memread',hex(addr),128,1)['hex'])
                trace=genre_trace.choose(pair)
                if trace['genre']!=expected_genre:raise ValueError(f'expected {expected_genre} trace, got {trace["genre"]}')
                if (trace['buttons'] & 0xff)!=mask:
                    raise ValueError(f'game input trace did not latch requested controller buttons: expected {mask}, got {trace["buttons"] & 0xff}')
                captures.append({'file':str(path),'frame':trace['frame'],'screen_x':trace['screen_x'],
                                 'state':trace['state'],'buttons':trace['buttons']})
    finally:client.close()
    if len(captures)<2:raise ValueError('scenario must capture at least two images')
    proof=check_pngs(captures[0]['file'],captures[-1]['file'],scenario.get('expect',{}))
    if captures[-1]['frame']<=captures[0]['frame']:
        raise ValueError('game trace frame did not advance')
    expect_dx=scenario.get('expect',{}).get('player_dx')
    dx=captures[-1]['screen_x']-captures[0]['screen_x']
    if expect_dx=='positive' and dx<4:raise ValueError(f'player did not move right in trace: dx={dx}')
    if expect_dx=='negative' and dx>-4:raise ValueError(f'player did not move left in trace: dx={dx}')
    result={'result':'passed','genre':expected_genre,'screenshots':captures,'pixel_evidence':proof,
            'trace_screen_dx':dx,'limits':'emulator pixels + game-authored G2TR; not physical-console proof'}
    out.write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True);p.add_argument('--elf');p.add_argument('--scenario',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    try:print(json.dumps(run(a.rom,a.scenario,a.output,a.elf),indent=2))
    except (ValueError,RuntimeError,OSError) as e:p.error(str(e))
if __name__=='__main__':main()
