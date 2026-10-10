import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster/tools'))
import compare_presentation as c

class ComparisonTests(unittest.TestCase):
    def data(self,kind,redraws):
        rows=128 if kind=='full' else 64
        return {'result':'passed','render_mode':kind,'logical_pixels':[128,rows],
                'totals':{'completed_redraws':redraws,'emulator_frames':1080,'game_updates':250},
                'segments':[{'buttons':['right'],'emulator_frames':1080}]}
    def test_half_resolution_does_not_count_as_doubled_pixel_work(self):
        s=c.compare(self.data('full',16),self.data('atomic',31))
        self.assertEqual(s['full_resolution']['logical_pixels_processed'],262144)
        self.assertEqual(s['atomic_half_height']['logical_pixels_processed'],253952)
        self.assertEqual(s['relative_completed_pixel_work_pct'],96.88)
    def test_mismatched_scenarios_rejected(self):
        a=self.data('full',16);b=self.data('atomic',31)
        b['segments'][0]['buttons']=['left']
        with self.assertRaisesRegex(ValueError,'scenarios differ'):c.compare(a,b)
    def test_fabricated_geometry_rejected(self):
        a=self.data('full',16);b=self.data('atomic',31)
        b['logical_pixels']=[128,128]
        with self.assertRaisesRegex(ValueError,'geometry'):c.compare(a,b)
    def test_no_unverified_frame_claims(self):
        a=self.data('full',16);b=self.data('atomic',31)
        b['result']='failed'
        with self.assertRaisesRegex(ValueError,'independent screenshot'):c.compare(a,b)
if __name__=='__main__':unittest.main()
