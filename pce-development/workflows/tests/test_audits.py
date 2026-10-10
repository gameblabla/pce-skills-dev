import importlib.util
from pathlib import Path
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class AuditTests(unittest.TestCase):
    def test_animation_contract(self):
        data=json.loads((ROOT/'specs/animation.json').read_text())
        self.assertEqual(load('animation_audit').audit(data),[])
    def test_missing_idle_shoot_is_detected(self):
        data=json.loads((ROOT/'specs/animation.json').read_text())
        del data['states']['shoot_idle']
        self.assertIn('shoot_idle',str(load('animation_audit').audit(data)))
    def test_unsafe_sprite_path_rejected(self):
        data=json.loads((ROOT/'specs/animation.json').read_text())
        data['states']['idle']['frames']=['../../private.png']
        self.assertIn('unsafe',str(load('animation_audit').audit(data)))
    def test_collidable_platform_art_consistency(self):
        data=json.loads((ROOT/'specs/platforms.json').read_text())
        errors,info=load('map_audit').audit(data)
        self.assertEqual(errors,[]);self.assertEqual(len(info),4)
    def test_art_collision_top_shift_detected(self):
        data=json.loads((ROOT/'specs/platforms.json').read_text())
        data['surfaces'][1]['art'][1]+=8
        errors,_=load('map_audit').audit(data)
        self.assertIn('mismatch',str(errors))
    def test_pixel_tile_end_is_exclusive(self):
        data=json.loads((ROOT/'specs/platforms.json').read_text())
        _,info=load('map_audit').audit(data)
        ledge=info[1]
        self.assertEqual(ledge['left_tile'],13)
        self.assertEqual(ledge['right_tile'],18)

if __name__=='__main__':unittest.main()
