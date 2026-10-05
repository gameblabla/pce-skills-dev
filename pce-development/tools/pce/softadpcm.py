#!/usr/bin/env python3
"""Encode and decode the bundled SoftADPCM 2-bit software stream.

Codes are low pair first: +small, +large, -small, -large. Predictor is unsigned
16-bit, starts at 0x8000 and saturates; the ring-buffer output is its high byte.
The decoder lookup tables are bundled in softadpcm_tables.py and
softadpcm_tables.c; no source ROM is needed.
"""
import argparse
import array
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

from softadpcm_tables import LARGE_STEPS, NEXT_LARGE, NEXT_SMALL, SMALL_STEPS, TABLE_SHA256

def tables():
    return SMALL_STEPS,LARGE_STEPS,NEXT_SMALL,NEXT_LARGE

def advance(predictor,index,code,t):
    small,large,next_small,next_large=t
    magnitude=(large if code&1 else small)[index]
    predictor=max(0,min(65535,predictor+(-magnitude if code&2 else magnitude)))
    index=(next_large if code&1 else next_small)[index]
    return predictor,index

def decode(data,count,t):
    if count is None:count=len(data)*4
    if not 0<=count<=len(data)*4:raise ValueError('Invalid sample count')
    predictor,index=32768,0;out=[]
    for i in range(count):
        code=data[i>>2]>>((i&3)*2)&3
        predictor,index=advance(predictor,index,code,t)
        out.append((predictor>>8)-128)
    return out

def encode(pcm,t):
    predictor,index=32768,0;codes=[]
    for sample in pcm:
        target=max(0,min(65535,int(sample)+32768))
        candidates=[advance(predictor,index,c,t) for c in range(4)]
        code=min(range(4),key=lambda c:abs(candidates[c][0]-target))
        predictor,index=candidates[code];codes.append(code)
    return bytes(sum(c<<((i&3)*2) for i,c in enumerate(codes[start:start+4])) for start in range(0,len(codes),4))

def compress(src,dst,rate,tail_silence=32):
    if rate <= 0:raise ValueError('sample rate must be positive')
    if tail_silence < 0:raise ValueError('tail silence must not be negative')
    result=subprocess.run(['ffmpeg','-v','error','-i',str(src),'-ac','1','-ar',str(rate),
        '-af',f'lowpass=f={min(7000,rate*0.44):g}','-f','s16le','-'],check=True,capture_output=True)
    if len(result.stdout)&1:raise ValueError('ffmpeg returned a partial PCM sample')
    pcm=array.array('h');pcm.frombytes(result.stdout)
    if sys.byteorder!='little':pcm.byteswap()
    source_samples=len(pcm)
    pcm.extend([0]*tail_silence)
    t=tables()
    data=encode(pcm,t);dst=Path(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(data)
    reconstructed=decode(data,len(pcm),t)
    dda=bytes((v+128)>>3 for v in reconstructed)
    dst.with_suffix('.dda').write_bytes(dda)
    decoded=array.array('h',(v*256 for v in reconstructed))
    if sys.byteorder!='little':decoded.byteswap()
    with wave.open(str(dst.with_suffix('.decoded.wav')),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(decoded.tobytes())
    report=dict(format='softadpcm-2bit-low-pair-first-v1',source_samples=source_samples,
        samples=len(pcm),bytes=len(data),dda_bytes=len(dda),rate=rate,tail_silence_samples=tail_silence,
        predictor=32768,step_index=0,table_sha256=TABLE_SHA256,
        source_sha256=hashlib.sha256(Path(src).read_bytes()).hexdigest())
    dst.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Encode mono audio for the bundled SoftADPCM 2-bit decoder.')
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--rate',type=int,default=15734)
    p.add_argument('--tail-silence',type=int,default=32,help='zero PCM samples appended before encoding')
    a=p.parse_args();print(json.dumps(compress(a.input,a.output,a.rate,a.tail_silence)))
