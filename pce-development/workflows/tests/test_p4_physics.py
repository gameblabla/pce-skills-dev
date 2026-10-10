"""2000+ step differential test: target Q4 C physics vs separate host Python oracle."""
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'examples/26-platformer-starter'
SURFACES=[(0,176,512),(104,144,48),(208,120,48),(352,144,48)]
C='''#include <stdio.h>
#include <stdint.h>
#define KEY_1 1
#define KEY_RIGHT 32
#define KEY_LEFT 128
#include "platformer_q4.h"
int main(void) {
 P4Motion p; p4_reset(&p);
 int v;uint8_t events;
 while(scanf("%d",&v)==1){
  uint8_t b=p4_tick(&p,(uint8_t)v,&events);
  printf("%d %d %d %d %d %u %u %u %u %u\\n",p.x,p.y,p.vx,p.vy,p.camera,p.grounded,p.left,p.before_jump,events,b);
 }
 return 0;
}
'''

def oracle(p,mask):
 x,y,vx,vy,camera,grounded,left,previous_jump=p
 old_feet=y+256
 if mask&128 and not mask&32:vx=-16;left=1
 elif mask&32 and not mask&128:vx=16;left=0
 else:vx=0
 x+=vx;blocked=int(x<0 or x>(512-16)*16)
 x=max(0,min((512-16)*16,x))
 def overlaps(s):return x+13*16>s[0]*16 and x+3*16<(s[0]+s[2])*16
 if grounded and not any(y+256==top*16 and overlaps(s) for s in SURFACES for top in [s[1]]):grounded=0
 jump=bool(mask&1); events=0
 if jump and not previous_jump and grounded:
  grounded=0;vy=-80;events|=2
 previous_jump=jump
 if not grounded:
  vy=min(96,vy+4);y+=vy
 else:vy=0
 if not grounded and vy>=0:
  for sx,top,w in SURFACES:
   if old_feet<=top*16<=y+256 and overlaps((sx,top,w)):
    y=top*16-256;vy=0;grounded=1;events|=1;break
 camera=max(0,min((512-256)*16,x-104*16))
 return [x,y,vx,vy,camera,grounded,left,previous_jump],events,blocked

class PhysicsDifferentialTest(unittest.TestCase):
    def test_host_compiler_matches_model_across_random_controls(self):
        gcc=shutil.which('cc')
        if not gcc:self.skipTest('host C compiler not installed')
        # Right then jump off platforms; random turning, held jump and edges.
        rng=random.Random(0x6280)
        masks=[32]*380+[32|1]*21+[32]*50+[128]*200+[0]*80
        masks.extend(rng.choice([0,1,32,128,32|1,128|1,32|128,1]) for _ in range(1600))
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'sim.c';src.write_text(C)
            exe=Path(td)/'sim'
            subprocess.run([gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror',
                            '-I'+str(SOURCE/'src'),'-I'+str(SOURCE/'assets'),str(src),'-o',str(exe)],check=True)
            run=subprocess.run([str(exe)],input='\n'.join(map(str,masks))+'\n',text=True,
                               stdout=subprocess.PIPE,check=True)
        records=[[int(x) for x in line.split()] for line in run.stdout.splitlines()]
        self.assertEqual(len(records),len(masks))
        p=[32*16,(176-16)*16,0,0,0,1,0,0]
        landed=jumped=0
        for i, (mask,actual) in enumerate(zip(masks,records)):
            p,events,blocked=oracle(p,mask)
            self.assertEqual(actual,p+[events,blocked],f'host target differs at tick {i}: input={mask}')
            landed+=bool(events&1);jumped+=bool(events&2)
        self.assertGreater(jumped,0)
        self.assertGreater(landed,0)

if __name__=='__main__':unittest.main()
