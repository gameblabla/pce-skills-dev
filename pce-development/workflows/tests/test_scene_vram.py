"""VRAM audits against actual generated HuCard C assets."""
import importlib.util
from pathlib import Path
import json
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scene_vram',ROOT/'scene_vram.py')
# scene_vram imports sibling module: ensure path available
import sys
sys.path.insert(0,str(ROOT))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class SceneVramTests(unittest.TestCase):
    def test_generated_shmup_and_racer(self):
        for name in ('33-rendered-shmup','35-rendered-racer'):
            with self.subTest(name=name):
                r=s.analyze(ROOT.parent/'examples'/name)
                self.assertTrue(r['ok'])
                self.assertLessEqual(r['boot_upload']['frames_used'],32)
                self.assertEqual(r['scene_arrays_bytes']['bat'],1792)

    def test_mismatched_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'src').mkdir()
            origin=ROOT.parent/'examples/33-rendered-shmup/src'
            for name in ('scene_manifest.json','scene_assets.h'):
                shutil.copy(origin/name,p/'src'/name)
            data=json.loads((p/'src/scene_manifest.json').read_text())
            data['vram_word_ranges']['bg'][1]-=1
            (p/'src/scene_manifest.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'overflows'):s.analyze(p)

    def test_wrong_sprite_count_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'src').mkdir()
            origin=ROOT.parent/'examples/33-rendered-shmup/src'
            for name in ('scene_manifest.json','scene_assets.h'):
                shutil.copy(origin/name,p/'src'/name)
            h=p/'src/scene_assets.h';h.write_text(h.read_text().replace('scene_sprites[512]','scene_sprites[1024]'))
            with self.assertRaises(ValueError):s.analyze(p)

    def test_overbudget_is_fail_not_silent(self):
        r=s.analyze(ROOT.parent/'examples/33-rendered-shmup',bytes_per_frame=32,max_frames=2)
        self.assertFalse(r['ok'])

if __name__=='__main__':unittest.main()
