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
        xx=get_table(data,'ray_step_x',16*64)
        yy=get_table(data,'ray_step_y',16*64)
        for angle in range(16):
            for column in range(64):
                side=column-32
                dx=r.COS[angle]-r.truncdiv(r.SIN[angle]*side,80)
                dy=r.SIN[angle]+r.truncdiv(r.COS[angle]*side,80)
                self.assertEqual(xx[angle*64+column],r.truncdiv(dx,2))
                self.assertEqual(yy[angle*64+column],r.truncdiv(dy,2))

    def test_bitmap_height_and_texel_lookup(self):
        data=r.generate()
        heights=get_table(data,'wall_height',33)
        texels=get_table(data,'wall_tex_v',33*64)
        self.assertEqual(get_table(data,'floor_shift',128)[:66],[0]*66)
        for depth,h in enumerate(heights):
            self.assertEqual(h,max(12,min(116,360//(depth+2))))
            self.assertLessEqual(h,116)
            self.assertGreaterEqual(h,12)
            row=texels[depth*64:(depth+1)*64]
            self.assertTrue(all(0<=v<=15 for v in row))
            for sample in range(64):
                self.assertEqual(row[sample],(sample*32)//h if sample*2<h else 0)
        self.assertTrue(all(heights[i]>=heights[i+1] for i in range(32)))

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
