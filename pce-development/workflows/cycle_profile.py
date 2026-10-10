#!/usr/bin/env python3
"""Reproducible HuC6280 *emulated master-clock* profiler, by physical ROM symbol.

Use the headless Mednafen fork's prof_start/prof_dump RPC; no patched ROM,
no network and no debugger's logical-PC hit-count approximation. Sampling
is self time (including callees that LLVM inlines), NOT a call graph.

A period spent waiting for VBlank is still real executed CPU time; report
it separately when its physical instruction PCs are supplied in a manifest.
Never call these measurements physical-console timing or host wall-clock FPS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PADS={'i':0,'ii':1,'select':2,'run':3,'up':4,'right':5,'down':6,'left':7}
MAX_PHYSICAL=1<<21


def read_profile(path):
    """RPC prof_dump format: one physical byte address (hex) and count."""
    totals={}
    for line_no,line in enumerate(Path(path).read_text().splitlines(),1):
        parts=line.split()
        if not parts: continue
        if len(parts)!=2 or not re.fullmatch(r'[0-9a-fA-F]{1,6}',parts[0]) or not re.fullmatch(r'[0-9]+',parts[1]):
            raise ValueError(f'bad profiler record at line {line_no}')
        a=int(parts[0],16);v=int(parts[1])
        if a>=MAX_PHYSICAL or a in totals or v<=0:
            raise ValueError(f'duplicate, zero, or out-of-range profiler address at line {line_no}')
        totals[a]=v
    if not totals: raise ValueError('no profiling samples (does the emulator support prof_start?)')
    return totals


def rom_labels(path):
    """Read exactly the physical *ROM offset* ranges in LLVM-MOS's MLB map."""
    spans=[]
    for line in Path(path).read_text().splitlines():
        m=re.fullmatch(r'PcePrgRom:([0-9a-fA-F]+)(?:-([0-9a-fA-F]+))?:([^\s:]+)',line.strip())
        if not m: continue
        lo=int(m[1],16);hi=int(m[2],16) if m[2] else lo
        if lo>hi or hi>=MAX_PHYSICAL:raise ValueError('invalid physical ROM span')
        # LLVM-MOS assembly exports a singleton label unless both .type and
        # .size are declared. Treating that as a one-byte IRQ once made an
        # optimization falsely appear to save 99% of its cycle budget.
        if m[3]=='irq_vdc' and lo==hi:
            raise ValueError('irq_vdc has no ROM span: assembly handler needs .type and .size for cycle attribution')
        spans.append((lo,hi,m[3]))
    if not spans:raise ValueError('no PcePrgRom symbols: require an LLVM-MOS .mlb file')
    spans.sort(key=lambda x:(x[0],x[1]-x[0]))
    return spans


def find_ram_symbol(path,name):
    for line in Path(path).read_text().splitlines():
        match=re.fullmatch(r'PceWorkRam:([0-9a-fA-F]+)(?:-([0-9a-fA-F]+))?:([^\s:]+)',line.strip())
        if match and match[3]==name:
            start=int(match[1],16)
            end=int(match[2],16) if match[2] else start
            return 0x2000+start, end-start+1
    raise ValueError(f'cannot find main RAM symbol {name} in MLB')


def read_progress(rpc,mlb,progress):
    if not progress:return None
    name=progress['ram_symbol']
    address,length=find_ram_symbol(mlb,name)
    if progress.get('kind','counter')=='g2tr':
        if length!=128:raise ValueError('G2TR progress trace must span two 64-byte slots')
        records=bytes.fromhex(rpc.call('memread',address,128,1)['hex'])
        candidates=[]
        for pos in (0,64):
            part=records[pos:pos+64]
            if part[:4]==b'G2TR' and part[4]==2 and not (int.from_bytes(part[14:16],'little')&1):
                candidates.append(int.from_bytes(part[8:12],'little'))
        if not candidates:raise ValueError('G2TR not yet published; increase warmup_frames')
        return max(candidates)
    width=progress.get('width',2)
    if width not in (1,2) or length<width:raise ValueError('counter requires width 1/2 and matching symbol range')
    return int.from_bytes(bytes.fromhex(rpc.call('memread',address,width,1)['hex']),'little')


def mapped_names(labels,cycles):
    """Pick the *smallest* explicit span if multiple aliases overlap.

    An unbounded (singleton) label gets only its own byte. This avoids
    extending an unrelated data symbol through an unknown ROM-code region.
    """
    boundaries={}
    for lo,hi,name in labels:
        for a in range(lo,hi+1):
            old=boundaries.get(a)
            if old is None or hi-lo<old[0]:boundaries[a]=(hi-lo,name)
    symbols={};unknown=0
    for pc,count in cycles.items():
        name=boundaries.get(pc,(None,'<unmapped>'))[1]
        symbols[name]=symbols.get(name,0)+count
        if name=='<unmapped>':unknown+=count
    return symbols,unknown


def classify(name):
    if name.startswith(('irq_', 'nmi', 'pce_hblank', 'pce_vblank')):return 'interrupt'
    if name.startswith('__') or name in ('_start','_init','_fini','exit','_early_start'):
        return 'runtime'
    if name=='<unmapped>':return 'unmapped'
    if name.startswith(('.L', 'main.', 'irq_')):return 'local'
    return 'application'


def summarize(cycles,labels,frames,limit=20):
    if not isinstance(frames,int) or not 1<=frames<=3600:raise ValueError('invalid frame count')
    names,unknown=mapped_names(labels,cycles)
    total=sum(cycles.values())
    if total<frames*250000 or total>frames*500000:
        raise ValueError(f'profiler total {total} outside plausible NTSC frame range for {frames} frames; check emulator timing')
    grouped={}
    for n,v in names.items():grouped[classify(n)]=grouped.get(classify(n),0)+v
    rows=[{'symbol':name,'category':classify(name),'ticks':v,
           'ticks_per_frame':round(v/frames,2),'pct':round(100*v/total,3)}
          for name,v in sorted(names.items(),key=lambda x:(-x[1],x[0]))]
    pcs=[{'physical_pc':f'0x{a:06X}','ticks':c,'pct':round(100*c/total,3)}
         for a,c in sorted(cycles.items(),key=lambda x:-x[1])[:limit]]
    return {'frames':frames,'master_clock_ticks':total,
            'master_clock_ticks_per_frame':round(total/frames,2),
            'tick_unit':'emulated HuC6280 master clock (not CPU instruction count or CPU core cycles)',
            'attribution':'physical ROM offset; function SELF time, inlined callees included in caller',
            'attributed_pct':round(100*(total-unknown)/total,2),
            'categories':grouped,'functions':rows,'hot_addresses':pcs,
            'unmapped_master_ticks':unknown}


def validate_scenario(data):
    if not isinstance(data,dict) or not isinstance(data.get('segments'),list) or not 1<=len(data['segments'])<=12:
        raise ValueError('scenario must contain 1..12 named segments')
    warmup=data.get('warmup_frames',120)
    if not isinstance(warmup,int) or not 0<=warmup<=1200:raise ValueError('warmup_frames must be 0..1200')
    total=0;names=set()
    for s in data['segments']:
        if not isinstance(s,dict) or not isinstance(s.get('name'),str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',s['name']) or s['name'] in names:
            raise ValueError('segments need unique safe names')
        names.add(s['name'])
        if not isinstance(s.get('frames'),int) or not 2<=s['frames']<=1200:raise ValueError('segment frames must be 2..1200')
        total+=s['frames']
        if not isinstance(s.get('buttons',[]),list) or any(b not in PADS for b in s.get('buttons',[])):
            raise ValueError(f'unknown buttons in {s["name"]}')
    if total>3600:raise ValueError('total measured frames must be <=3600')
    progress=data.get('progress')
    if progress is not None:
        if not isinstance(progress,dict) or progress.get('kind','counter') not in ('counter','g2tr') or not isinstance(progress.get('ram_symbol'),str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.]*',progress['ram_symbol']):
            raise ValueError('progress must identify a RAM symbol and kind counter/g2tr')
        if progress.get('kind','counter')=='counter' and progress.get('width',2) not in (1,2):
            raise ValueError('only 1/2-byte counters supported')
    return data


class RPC:
    def __init__(self,exe,rom,base):
        base.mkdir(parents=True,exist_ok=True)
        self.proc=subprocess.Popen([str(exe),'--rom',str(rom),'--base-dir',str(base),'--frames','1','--rpc'],
                                   stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
    def call(self,op,*args):
        if self.proc.poll() is not None:raise ValueError('emulator quit unexpectedly')
        self.proc.stdin.write('\t'.join((op,*map(str,args)))+'\n');self.proc.stdin.flush()
        out=self.proc.stdout.readline()
        if not out:raise ValueError(f'emulator closed RPC while running {op}')
        data=json.loads(out)
        if not data.get('ok'):raise ValueError(f'RPC {op}: {data.get("error","unknown error")}')
        return data
    def close(self):
        if self.proc.poll() is None:
            try:self.call('quit')
            except (ValueError,OSError,BrokenPipeError):self.proc.terminate()
            self.proc.wait(timeout=5)


def report_markdown(report):
    lines=['# Measured HuC6280 cycles by function', '',
       f'ROM SHA-256: `{report["rom_sha256"]}`',
       '', '| Segment | Frames | master ticks/frame | ROM attribution |',
       '|---|---:|---:|---:|']
    for name,s in report['segments'].items():
        lines.append(f'| {name} | {s["frames"]} | {s["master_clock_ticks_per_frame"]:,.0f} | {s["attributed_pct"]}% |')
    for name,s in report['segments'].items():
        lines += ['',f'## {name}', '', '| Routine / symbol | Category | ticks/frame | share |', '|---|---|---:|---:|']
        for x in s['functions'][:20]:
            lines.append(f'| `{x["symbol"]}` | {x["category"]} | {x["ticks_per_frame"]:,.1f} | {x["pct"]}% |')
    if any('game_updates' in segment for segment in report['segments'].values()):
        lines += ['', '| Segment | Completed game updates | Updates / emulator frame | Master ticks / update (incl. idle) |', '|---|---:|---:|---:|']
        for name,segment in report['segments'].items():
            if 'game_updates' in segment:
                lines.append(f'| {name} | {segment["game_updates"]} | {segment["updates_per_emulator_frame"]} | {segment["master_ticks_per_game_update"]:,.1f} |')
    lines += ['', '**Interpretation:** These are emulator master-clock ticks charged to instruction PCs, not wall-time FPS or measured hardware CPU cycles. A busy-wait loop can dominate the total. Symbol boundaries are from the linked `.mlb` ROM map; optimized/inlined functions may appear inside callers. `unmapped` is shown rather than guessed. Memory/bus waits and IRQ code are included. No real hardware timings are claimed.', '']
    return '\n'.join(lines)


def profile(exe,rom,mlb,scenario,out):
    data=validate_scenario(json.loads(Path(scenario).read_text()))
    labels=rom_labels(mlb)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    exe=Path(exe).resolve();rom=Path(rom).resolve()
    for p in (exe,rom):
        if not p.is_file():raise ValueError(f'missing executable or ROM: {p}')
    results={}
    rpc=RPC(exe,rom,out/'emulator-state')
    try:
        if data.get('warmup_frames',120):rpc.call('run',data.get('warmup_frames',120))
        for seg in data['segments']:
            mask=sum(1<<PADS[b] for b in set(seg.get('buttons',[])))
            rpc.call('input',mask)
            before=read_progress(rpc,mlb,data.get('progress'))
            rpc.call('prof_start')
            rpc.call('run',seg['frames'])
            raw=out/(seg['name']+'.cycles')
            raw.unlink(missing_ok=True)
            rpc.call('prof_dump',str(raw))
            after=read_progress(rpc,mlb,data.get('progress'))
            results[seg['name']]=summarize(read_profile(raw),labels,seg['frames'])
            results[seg['name']]['buttons']=seg.get('buttons',[])
            if before is not None:
                mask_counter=0xffffffff if data['progress'].get('kind')=='g2tr' else (1<<(8*data['progress'].get('width',2)))-1
                advances=(after-before)&mask_counter
                if advances>seg['frames']*6:raise ValueError(f'implausible game-counter advancement: {advances}')
                if advances==0:raise ValueError(f'game loop stalled during {seg["name"]}: zero game updates')
                results[seg['name']]['game_updates']=advances
                results[seg['name']]['updates_per_emulator_frame']=round(advances/seg['frames'],3)
                results[seg['name']]['master_ticks_per_game_update']=round(results[seg['name']]['master_clock_ticks']/advances,1)
    finally:rpc.close()
    report={'format':'pce-master-clock-symbol-profile-v1',
            'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
            'scenario':str(Path(scenario).resolve()),'symbol_map':str(Path(mlb).resolve()),
            'emulator':str(exe),'segments':results,
            'limitations':['Mednafen emulation, not real hardware',
              'Includes idle busy-waits, interrupts and memory access stalls',
              'ROM symbols are self time; inlining may combine routines',
              'No hardware cycle accuracy or game FPS claim']}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'report.md').write_text(report_markdown(report))
    return report


def check_budget(report,limits):
    """Explicit per-symbol/per-category limits, never an idle-blind total."""
    if report.get('format')!='pce-master-clock-symbol-profile-v1':
        raise ValueError('not a cycle-profile report')
    if not isinstance(limits,dict) or not isinstance(limits.get('segments'),dict):
        raise ValueError('budget requires segments object')
    issues=[]
    for name,b in limits['segments'].items():
        if name not in report['segments']:raise ValueError(f'budget segment missing from trace: {name}')
        if not isinstance(b,dict):raise ValueError('segment budget must be an object')
        s=report['segments'][name]
        if 'min_attributed_pct' in b:
            bound=b['min_attributed_pct']
            if not isinstance(bound,(int,float)) or not 0<bound<=100:
                raise ValueError('min_attributed_pct must be in (0,100]')
            if s.get('attributed_pct',0)<bound:
                issues.append(f'{name}: only {s.get("attributed_pct",0):.2f}% of cycles have a ROM symbol; require >= {bound}%')
        if 'min_game_updates' in b:
            bound=b['min_game_updates']
            if not isinstance(bound,int) or bound<1:raise ValueError('min_game_updates must be positive integer')
            if s.get('game_updates',0)<bound:
                issues.append(f'{name}: game advanced {s.get("game_updates",0)} times; require >= {bound}')
        for sym,cap in b.get('max_ticks_per_frame_by_symbol',{}).items():
            if not isinstance(cap,(int,float)) or cap<=0:raise ValueError('invalid maximum ticks/frame')
            values=[x['ticks_per_frame'] for x in s['functions'] if x['symbol']==sym]
            if not values:
                issues.append(f'{name}: required symbol {sym} is missing from measured execution')
                continue
            actual=values[0]
            if actual>cap:issues.append(f'{name}: {sym} {actual:.1f} > {cap:.1f} ticks/frame')
        for category,cap in b.get('max_pct_by_category',{}).items():
            if category not in ('interrupt','application','runtime','local','unmapped') or not isinstance(cap,(int,float)) or cap<0 or cap>100:
                raise ValueError('invalid category or maximum percent')
            actual=100*s['categories'].get(category,0)/s['master_clock_ticks']
            if actual>cap:issues.append(f'{name}: {category} {actual:.2f}% > {cap:.2f}%')
    return {'result':'passed' if not issues else 'failed','issues':issues}


def diff_reports(old,new):
    if old.get('format')!='pce-master-clock-symbol-profile-v1' or new.get('format')!=old['format']:
        raise ValueError('incompatible report format')
    if old['rom_sha256']==new['rom_sha256']:
        raise ValueError('expected distinct baseline and optimized ROMs')
    out={}
    for name,a in old['segments'].items():
        if name not in new['segments']:raise ValueError('baseline segment absent from optimized run')
        b=new['segments'][name]
        if a['frames']!=b['frames'] or a.get('buttons')!=b.get('buttons'):
            raise ValueError('different frame count or input; comparison invalid')
        old_updates=a.get('game_updates');new_updates=b.get('game_updates')
        comparable=(old_updates is not None and new_updates is not None and old_updates==new_updates)
        x={row['symbol']:row['ticks_per_frame'] for row in a['functions']}
        y={row['symbol']:row['ticks_per_frame'] for row in b['functions']}
        out[name]={'baseline_ticks_per_frame':a['master_clock_ticks_per_frame'],
                   'optimized_ticks_per_frame':b['master_clock_ticks_per_frame'],
                   'baseline_game_updates':old_updates,'optimized_game_updates':new_updates,
                   'routine_cost_comparable':comparable,
                   'per_symbol_delta_ticks_per_frame':(
                     {n:round(y.get(n,0)-x.get(n,0),2) for n in sorted(set(x)|set(y))}
                     if comparable else None),
                   'note':('Same update count, but execution state still needs inspection; changed symbol boundaries or inlining can invalidate comparisons.'
                      if comparable else 'NOT COMPARABLE: update counts differ or no game-state counter; do not claim routine speedups from this phase.')}

    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run',help='profile named input phases on an existing ROM')
    for f in ('emulator','rom','mlb','scenario','out'):run.add_argument('--'+f,required=True)
    gate=sub.add_parser('gate',help='validate emulated function/IRQ budgets')
    gate.add_argument('--report',required=True);gate.add_argument('--budget',required=True)
    compare=sub.add_parser('compare',help='compare two saved profiles of identical input')
    compare.add_argument('--baseline',required=True);compare.add_argument('--optimized',required=True)
    compare.add_argument('--out')
    a=ap.parse_args()
    try:
        if a.command=='run':
            result=profile(a.emulator,a.rom,a.mlb,a.scenario,a.out)
            print(json.dumps({k:{'frames':v['frames'],'ticks_per_frame':v['master_clock_ticks_per_frame'],
               'attributed_pct':v['attributed_pct'],'top_functions':v['functions'][:5]}
               for k,v in result['segments'].items()},indent=2))
        elif a.command=='gate':
            result=check_budget(json.loads(Path(a.report).read_text()),json.loads(Path(a.budget).read_text()))
            print(json.dumps(result,indent=2))
            if result['issues']:sys.exit(1)
        else:
            result=diff_reports(json.loads(Path(a.baseline).read_text()),json.loads(Path(a.optimized).read_text()))
            text=json.dumps(result,indent=2)+'\n'
            if a.out:Path(a.out).write_text(text)
            print(text)
    except (OSError,ValueError,subprocess.SubprocessError,json.JSONDecodeError) as e:ap.error(str(e))

if __name__=='__main__':main()
