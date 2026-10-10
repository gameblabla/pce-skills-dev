"""Host-only negative checks for compact Q4 state and independently grounded traces."""
from pathlib import Path
import importlib.util
import struct
import unittest
import sys

BASE=Path(__file__).resolve().parents[2]
PROJECT=BASE/'examples/26-platformer-starter'
sys.path.insert(0,str(PROJECT/'tools'))
spec=importlib.util.spec_from_file_location('p4_trace',PROJECT/'tools/p4_trace.py')
trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)

class CompactPlatformerTests(unittest.TestCase):
    def setUp(self):
        self.world=trace.geometry(PROJECT/'assets/platform_layout.h')
        self.sample=dict(version=4,scene=0,flags=1,events=0,sequence=2,buttons=0,
                         frame=1,x_q4=512,y_q4=2560,vx_q4=0,vy_q4=0,camera_q4=0,
                         draw_x=35,draw_y=161,race_lane=0,race_progress=0,
                         surface_count=4,live_sprites=1)
    def test_size_and_valid_decode(self):
        self.assertEqual(trace.RECORD.size,32)
        v=[b'P4TR',4,0,1,0,2,0,1,512,2560,0,0,0,35,161,0,0,4,1]
        packed=trace.RECORD.pack(*v)
        self.assertEqual(trace.decode(packed)['x_q4'],512)
        self.assertEqual(trace.select(packed+bytes(32))['frame'],1)
    def test_partial_publish_rejected(self):
        buf=bytearray(trace.RECORD.pack(b'P4TR',4,0,1,0,3,0,1,512,2560,0,0,0,35,161,0,0,4,1))
        with self.assertRaises(ValueError):trace.decode(buf)
        with self.assertRaises(ValueError):trace.select(buf+bytes(32))
    def test_correct_support(self):
        self.assertTrue(trace.audit([self.sample],self.world)['ok'])
    def test_fake_grounded(self):
        bad=dict(self.sample,y_q4=64*16,draw_y=65)
        self.assertIn('grounded_without_support',[x['issue'] for x in trace.audit([bad],self.world)['issues']])
    def test_wrong_camera_and_sprite(self):
        bad=dict(self.sample,draw_x=100,camera_q4=64)
        issues=[x['issue'] for x in trace.audit([bad],self.world)['issues']]
        self.assertIn('camera_follow_mismatch',issues)
        self.assertIn('visual_collision_box_mismatch',issues)
    def test_teleport_and_race_regression(self):
        old=dict(self.sample,scene=1,frame=1,race_lane=128,race_progress=200)
        new=dict(old,frame=2,race_progress=190)
        self.assertIn('race_progress_reversed',[x['issue'] for x in trace.audit([old,new],self.world)['issues']])
    def test_scene_roundtrip_required(self):
        self.assertIn('missing_platformer_racer_roundtrip',
                      [x['issue'] for x in trace.audit([self.sample],self.world,True)['issues']])
    def test_unsafe_scenarios_rejected(self):
        for bad in [[{'frames':0,'buttons':[]}],
                    [{'frames':3700,'buttons':[]}],
                    [{'frames':1,'buttons':['a']}],
                    [{'frames':1,'buttons':['i','i']}]]:
            with self.assertRaises(ValueError):trace.scenario_steps(bad)
    def test_duplicate_headers_stay_identical(self):
        other=BASE/'examples/27-platformer-racer'
        for name in ('src/platformer_q4.h','tools/p4tr.h','tools/p4_trace.py','tools/headless_rpc.py'):
            self.assertEqual((PROJECT/name).read_bytes(),(other/name).read_bytes(),name)

if __name__=='__main__':unittest.main()
