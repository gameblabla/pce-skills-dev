#!/usr/bin/env python3
"""Offline HuC6270 VRAM layout and frame-transfer planner.

Coordinates and capacities are in VRAM **words** (0..0x7fff); transfers are
**bytes**. CPU upload budgets and interrupt-safe chunk sizes are caller-supplied
planning assumptions, NOT measured timings or guaranteed VBlank capacity.

Use this before writing BAT, sprite patterns or SAT copy code. A successful
plan only proves allocations and byte budgets, not that an emulator displays
correct frames or that an IRQ handler will meet deadlines.

Progressive visible BAT edits may be declared with `progressive_visible=true`,
which explicitly acknowledges tearing; they must use raster IRQs and chunks
<=16 bytes and cannot also claim VBlank-only publishing. This planner checks
only *linear allocation spans*, not VDC vertical address-increment semantics.
Active raster transfers must be <=16 bytes; explicitly VBlank-only uploads
may use an additional, separately declared bounded TIA chunk size. This does
NOT assert a given VBlank has enough actual HuC6280 cycles: that requires a
cycle profile and the emulator screenshot/interrupt stress tests.
"""
import argparse
import json
from pathlib import Path

VRAM_WORDS = 0x8000
MAX_ITEMS = 1024


def integer(value, name, low=0, high=65535):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in {low}..{high}')
    return value


def parse(spec):
    if not isinstance(spec, dict):
        raise ValueError('input must be a JSON object')
    system=spec.get('system','pce')
    if system not in ('pce','supergrafx'):
        raise ValueError('system must be pce or supergrafx')
    vdcs=2 if system=='supergrafx' else 1
    budget=integer(spec.get('bytes_per_frame'), 'bytes_per_frame', 2, 32768)
    if budget & 1: raise ValueError('bytes_per_frame must be even')
    frames=integer(spec.get('max_frames',16), 'max_frames', 1, 10000)
    raster=spec.get('raster_irqs',False)
    if type(raster)!=bool: raise ValueError('raster_irqs must be boolean')
    chunk=integer(spec.get('max_chunk_bytes',16 if raster else 64),'max_chunk_bytes',2,256)
    if chunk&1:raise ValueError('max_chunk_bytes must be even')
    vblank_chunk=integer(spec.get('vblank_max_chunk_bytes',chunk),'vblank_max_chunk_bytes',2,1024)
    if vblank_chunk&1:raise ValueError('vblank_max_chunk_bytes must be even')
    # Saber Rider's old scanline IRQ had very little interrupt latency slack.
    # A long HuC6280 block transfer is not IRQ-preemptible.
    if raster and chunk>16:
        raise ValueError('raster_irqs=true requires max_chunk_bytes <= 16; split TIA/TAI bursts')
    regions=spec.get('regions',[])
    uploads=spec.get('uploads',[])
    if not isinstance(regions,list) or len(regions)>MAX_ITEMS:raise ValueError('regions must be a bounded list')
    if not isinstance(uploads,list) or len(uploads)>MAX_ITEMS:raise ValueError('uploads must be a bounded list')
    named={};banks=[[] for _ in range(vdcs)]
    for r in regions:
        if not isinstance(r,dict):raise ValueError('region must be an object')
        name=r.get('id')
        if not isinstance(name,str) or not name or name in named:raise ValueError('region IDs must be nonempty and unique')
        vdc=integer(r.get('vdc',0),f'{name}.vdc',0,vdcs-1)
        at=integer(r.get('start_word'),f'{name}.start_word',0,VRAM_WORDS-1)
        size=integer(r.get('words'),f'{name}.words',1,VRAM_WORDS)
        if at+size>VRAM_WORDS:raise ValueError(f'{name}: allocation exceeds 0x8000 VRAM words')
        visibility=r.get('visibility','static')
        if visibility not in ('static','front','back'):raise ValueError(f'{name}: bad visibility')
        for other in banks[vdc]:
            if at<other['end_word'] and at+size>other['start_word']:
                raise ValueError(f'{name}: VRAM overlap with {other["id"]} in VDC{vdc}')
        data={'id':name,'vdc':vdc,'start_word':at,'end_word':at+size,'words':size,'visibility':visibility}
        named[name]=data;banks[vdc].append(data)
    requests=[];usedids=set(); transfer_ranges={}
    for order,u in enumerate(uploads):
        if not isinstance(u,dict):raise ValueError('upload must be an object')
        name=u.get('id')
        if not isinstance(name,str) or not name or name in usedids:
            raise ValueError('upload IDs must be nonempty and unique')
        usedids.add(name)
        region=named.get(u.get('region'))
        if not region:raise ValueError(f'{name}: unknown region')
        offset=integer(u.get('offset_words',0),f'{name}.offset_words',0,VRAM_WORDS)
        count=integer(u.get('bytes'),f'{name}.bytes',2,65536)
        if count&1:raise ValueError(f'{name}: byte count must be even')
        if offset+count//2>region['words']:raise ValueError(f'{name}: transfer exceeds {region["id"]}')
        for start,end,other in transfer_ranges.get(region['id'],[]):
            if offset<end and offset+count//2>start:
                raise ValueError(f'{name}: target range overlaps upload {other}')
        transfer_ranges.setdefault(region['id'],[]).append((offset,offset+count//2,name))
        early=integer(u.get('earliest_frame',0),f'{name}.earliest_frame',0,frames-1)
        deadline=integer(u.get('deadline_frame',frames-1),f'{name}.deadline_frame',early,frames-1)
        if 'vblank_only' in u and type(u['vblank_only'])!=bool:
            raise ValueError(f'{name}: vblank_only must be boolean')
        if 'progressive_visible' in u and type(u['progressive_visible'])!=bool:
            raise ValueError(f'{name}: progressive_visible must be boolean')
        progressive=u.get('progressive_visible',False)
        if progressive and u.get('vblank_only',False):
            raise ValueError(f'{name}: progressive_visible contradicts vblank_only')
        if progressive and (region['visibility']!='front' or not raster):
            raise ValueError(f'{name}: progressive_visible requires a front BAT region and raster_irqs=true')
        if region['visibility']=='front' and not u.get('vblank_only',False) and not progressive:
            raise ValueError(f'{name}: writing visible VRAM requires explicit vblank_only=true or progressive_visible=true')
        requests.append({'id':name,'region':region,'offset':offset,'total_bytes':count,
                         'vblank_only':u.get('vblank_only',False),'progressive_visible':progressive,
                         'remaining_bytes':count,'earliest':early,'deadline':deadline,'order':order})
    if sum(r['total_bytes'] for r in requests)>4*1024*1024:
        raise ValueError('total scheduled uploads exceed 4 MiB offline planning limit')
    return budget,frames,chunk,vblank_chunk,raster,requests,banks


def plan(spec):
    budget,frames,chunk,vblank_chunk,raster,requests,banks=parse(spec)
    timeline=[]
    for frame in range(frames):
        room=budget
        allocations=[]
        # Earliest deadline first, stable on input order. Every chunk has a
        # separate IRQ opportunity, unlike a single uninterruptible TIA block.
        active=sorted((r for r in requests if r['earliest']<=frame and r['remaining_bytes']),
                      key=lambda r:(r['deadline'],r['order']))
        for req in active:
            while room>=2 and req['remaining_bytes']:
                limit=vblank_chunk if req['vblank_only'] else chunk
                n=min(room,limit,req['remaining_bytes']) & ~1
                addr=req['region']['start_word']+req['offset']+(req['total_bytes']-req['remaining_bytes'])//2
                allocations.append({'id':req['id'],'region':req['region']['id'],'vdc':req['region']['vdc'],
                                    'start_word':addr,'bytes':n,'chunk_bytes':n,
                                    'vblank_only':req['vblank_only'],
                                    'progressive_visible':req['progressive_visible']})
                room-=n;req['remaining_bytes']-=n
        if allocations:
            timeline.append({'frame':frame,'bytes':budget-room,'chunks':allocations})
        if all(not r['remaining_bytes'] for r in requests):break
    incomplete=[{'id':r['id'],'remaining_bytes':r['remaining_bytes'],'deadline':r['deadline']}
                for r in requests if r['remaining_bytes']]
    late=[]
    for tick in timeline:
        for chunkinfo in tick['chunks']:
            r=next(r for r in requests if r['id']==chunkinfo['id'])
            if tick['frame']>r['deadline'] and r['id'] not in late:late.append(r['id'])
    # Transfers whose deadline passed with bytes left may be unschedulable
    # even if the last valid frame has not yet been planned.
    return {'ok':not incomplete and not late,'regions':sum(len(b) for b in banks),
            'vdc_count':len(banks),'raster_irqs':raster,
            'bytes_per_frame':budget,'max_chunk_bytes':chunk,
            'contains_progressive_visible_writes':any(r['progressive_visible'] for r in requests),
            'vblank_max_chunk_bytes':vblank_chunk,
            'scheduled_bytes':sum(t['bytes'] for t in timeline),
            'frames_used':len(timeline),'timeline':timeline,
            'incomplete':incomplete,'late_uploads':late,
            'limits':'Offline linear byte scheduling only: no VDC stride validation, measured CPU cycles, VBlank timing or hardware-proof claims. Progressive visible writes can tear.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('spec',type=Path)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--strict',action='store_true',help='nonzero exit on missed upload deadlines')
    args=ap.parse_args()
    try:
        report=plan(json.loads(args.spec.read_text()))
    except (ValueError,OSError) as e:
        ap.error(str(e))
    output=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output)
    print(output,end='')
    return 0 if report['ok'] or not args.strict else 1

if __name__=='__main__':raise SystemExit(main())
