"""Proof tables preserve the original raycaster's integer-truncation rules."""
import importlib.util
from pathlib import Path
import re
import unittest

PROJ=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
spec=importlib.util.spec_from_file_location('ray_tables',PROJ/'tools/gen_ray_tables.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def get_table(raw,name,rows):
    m=re.search(r'\b'+re.escape(name)+r'\[\d+\](?:\[\d+\])?\s*=\s*\{(.*?)\};',raw,re.S)
    if not m:raise ValueError(name)
    nums=[int(x) for x in re.findall(r'(?<!\w)-?\d+\b',m.group(1))]
    if len(nums)!=rows:raise ValueError(f'{name}: {len(nums)} != {rows}')
    return nums

class RayTableTests(unittest.TestCase):
    def test_generated_header_is_fresh(self):
        self.assertEqual(r.generate(),r.OUT.read_text())

    def test_ray_steps_match_signed_truncation(self):
        data=r.generate()
        xx=get_table(data,'ray_step_x',16*32)
        yy=get_table(data,'ray_step_y',16*32)
        for angle in range(16):
            for column in range(32):
                side=column-16
                dx=r.COS[angle]-r.truncdiv(r.SIN[angle]*side,40)
                dy=r.SIN[angle]+r.truncdiv(r.COS[angle]*side,40)
                self.assertEqual(xx[angle*32+column],r.truncdiv(dx,2))
                self.assertEqual(yy[angle*32+column],r.truncdiv(dy,2))

    def test_height_and_shade_exact(self):
        data=r.generate();heights=get_table(data,'wall_height',33)
        shades=get_table(data,'wall_shade',33)
        for depth in range(33):
            self.assertEqual(heights[depth],max(2,26//(1+depth//5)))
            self.assertEqual(shades[depth],14-min(5,depth//5))

    def test_traffic_accumulator_matches_integer_divide(self):
        phase=[0,0,0];rem=[0,0,0];distance=0
        for tick in range(2000):
            speed=(tick*7%4) # 0..3, varies often
            distance+=speed
            for i in range(3):
                q=rem[i]+speed;denom=i+1
                while q>=denom:
                    phase[i]=(phase[i]+1)%176
                    q-=denom
                rem[i]=q
                self.assertEqual(phase[i],(distance//denom)%176)

if __name__=='__main__':unittest.main()
