"""Small standalone headless RPC client (no legacy P2TR dependency)."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

class NativeControl:
    def __init__(self, binary, rom, base_dir, bios=None, initial_frames=2):
        cmd=[str(binary),'--rom',str(rom),'--base-dir',str(base_dir),'--frames',str(initial_frames),'--rpc']
        if bios:cmd+=['--bios',str(bios)]
        self.process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=sys.stderr,text=True,bufsize=1)
    def call(self,op,*args):
        if self.process.poll() is not None:raise RuntimeError('emulator exited before RPC command')
        self.process.stdin.write('\t'.join([op]+[str(x) for x in args])+'\n')
        self.process.stdin.flush()
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('emulator closed its RPC pipe')
        result=json.loads(line)
        if not result.get('ok'):raise RuntimeError(f'{op}: '+result.get('error','unknown RPC error'))
        return result
    def close(self):
        if self.process.poll() is None:
            try:self.call('quit')
            except Exception:self.process.terminate()
            self.process.wait(timeout=5)

def executable():
    if os.environ.get('PCE_HEADLESS'):return Path(os.environ['PCE_HEADLESS']).resolve()
    here=Path(__file__).resolve()
    for root in (here.parent, *here.parents):
        candidate=root/'pce-development/third_party'
        if candidate.is_dir():
            for exe in candidate.glob('*/pce-headless'):
                if exe.is_file() and os.access(exe,os.X_OK):return exe
    raise RuntimeError('PCE_HEADLESS is required for scripted emulator inputs')

def symbol(elf,name='p4_trace'):
    exe=os.environ.get('PCE_TRACE_NM') or shutil.which('llvm-nm')
    if not exe:raise RuntimeError('llvm-nm missing from PATH')
    result=subprocess.check_output([exe,'--defined-only',str(elf)],text=True)
    for line in result.splitlines():
        found=re.match(r'^\s*([0-9a-fA-F]+)\s+\w\s+(\S+)\s*$',line)
        if found and found.group(2)==name:
            address=int(found.group(1),16)
            if address>>16==0xf8:address&=0xffff
            if address<0x2000 or address+64>0x4000:raise ValueError('P4TR must live in main RAM')
            return address
    raise ValueError(f'ELF has no {name} symbol')
