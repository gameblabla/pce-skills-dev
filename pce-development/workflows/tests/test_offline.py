import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('offline',BASE/'offline.py')
offline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)
GOOD=BASE/'specs/hybrid.json'
SCENARIO=BASE/'specs/quick-test.json'

class OfflineWorkflowTests(unittest.TestCase):
    def fixture(self):return json.loads(GOOD.read_text())
    def test_routes_mixed(self):
        self.assertEqual(offline.choose('Contra-like platformer plus racing segments'), 'hybrid')
    def test_routes_platformer(self):
        self.assertEqual(offline.choose('simple jumping platformer'), 'platformer')
    def test_brief_stops_unverified_claims(self):
        brief=offline.agent_brief("Contra-style racing and platforming")
        self.assertIn("27-platformer-racer",brief)
        self.assertIn("Unverified features",brief)
        self.assertIn("make run",brief)
    def test_routes_narrow_math_to_libcommon(self):
        self.assertEqual(offline.choose('fast multiplication using libcommon'), 'math')
        brief=offline.agent_brief('fast multiplication using libcommon')
        self.assertIn('arith_guard.py elf',brief)
    def test_routes_sound_isolated(self):
        self.assertEqual(offline.choose('pure PSG sound effect'), 'audio')
    def test_routes_bitmap(self):
        self.assertEqual(offline.choose('racing Mode7 road'), 'racer')
    def test_valid_spec(self):
        self.assertEqual(len(offline.parse_spec(GOOD)['scenes']),2)
    def test_duplicate_scene_rejected(self):
        d=self.fixture();d['scenes'][1]['id']=d['scenes'][0]['id']
        self.assertBad(d)
    def test_bad_platform_bounds_rejected(self):
        d=self.fixture();d['scenes'][0]['platforms'][1]['x']=500
        self.assertBad(d)
    def test_negative_gravity_rejected(self):
        d=self.fixture();d['controls']['gravity_q8']=-64
        self.assertBad(d)
    def test_impossible_transition_rejected(self):
        d=self.fixture();d['scenes'][0]['next']='other'
        self.assertBad(d)
    def test_unimplemented_third_scene_rejected(self):
        d=self.fixture();d['scenes'].append(copy.deepcopy(d['scenes'][1]));d['scenes'][-1]['id']='third'
        self.assertBad(d)
    def test_bool_is_not_int(self):
        d=self.fixture();d['world']['width']=True
        self.assertBad(d)
    def test_generated_header_deterministic(self):
        d=self.fixture();txt=offline.generate_header(d)
        self.assertIn('#define HYBRID_GRAVITY_Q8 (64)',txt)
        self.assertEqual(txt,offline.generate_header(d))
        current=(BASE.parent/'examples/27-platformer-racer/src/hybrid_rules.h').read_text()
        self.assertEqual(current,txt)
    def test_oracle_stage_cycle(self):
        steps=json.loads(SCENARIO.read_text())['steps'];out=offline.simulate(self.fixture(),steps)
        labels=[f['scene'] for f in out['frames']]
        self.assertIn('highway',labels)
        self.assertEqual(labels[0],'fortress')
        self.assertEqual(labels[-1],'fortress')
    def test_lane_clamps(self):
        d=self.fixture();out=offline.simulate(d,[{'frames':200,'buttons':['right']},{'frames':500,'buttons':['left']}])
        self.assertGreaterEqual(out['final']['lane'],d['controls']['race_lane_left'])
        self.assertLessEqual(out['final']['lane'],d['controls']['race_lane_right'])
    def test_invalid_scenario(self):
        with self.assertRaises(ValueError): offline.simulate(self.fixture(),[{'frames':4,'buttons':['teleport']}])
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as work:
            target=Path(work)/'demo';target.mkdir()
            done=subprocess.run([sys.executable,str(BASE/'offline.py'),'new','--recipe','platformer','--out',str(target)],capture_output=True,text=True)
            self.assertNotEqual(done.returncode,0)
            self.assertIn('refusing overwrite',done.stderr)
    def test_scaffold_platformer(self):
        with tempfile.TemporaryDirectory() as work:
            target=Path(work)/'platform'
            done=subprocess.run([sys.executable,str(BASE/'offline.py'),'new','--recipe','platformer','--out',str(target)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertTrue((target/'src/main.c').exists());self.assertFalse((target/'build').exists())
    def test_scaffold_micro(self):
        with tempfile.TemporaryDirectory() as work:
            target=Path(work)/'audio'
            done=subprocess.run([sys.executable,str(BASE/'offline.py'),'new','--recipe','audio','--out',str(target)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertTrue((target/'micro/03-psg-tone/main.c').exists())
            self.assertTrue((target/'starter/tools/llvm-mos-sdk.mk').exists())
            self.assertTrue((target/'libcommon/src/fastmath.c').exists())
            self.assertTrue((target/'workflows/arith_guard.py').exists())
    def test_romcheck_rejects_bad(self):
        with tempfile.TemporaryDirectory() as work:
            f=Path(work)/'bad.pce';f.write_bytes(bytes(143))
            run=subprocess.run([sys.executable,str(BASE/'offline.py'),'romcheck',str(f)],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
    def assertBad(self,data):
        with tempfile.TemporaryDirectory() as work:
            p=Path(work)/'invalid.json';p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):offline.parse_spec(p)

if __name__=='__main__':unittest.main()
