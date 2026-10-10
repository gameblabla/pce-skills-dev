"""Offline visual-genre asset tooling: reproducibility and rejection gates."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
import scene_pack

class ScenePackTests(unittest.TestCase):
    def test_demo_compacts_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);scene_pack.demo('shmup',p)
            a=scene_pack.pack(p/'background.png',p/'sprites.png',p/'out')
            self.assertLess(a['unique_tiles'],896)
            first=(p/'out'/'scene_assets.c').read_bytes()
            b=scene_pack.pack(p/'background.png',p/'sprites.png',p/'out')
            self.assertEqual(a,b)
            self.assertEqual(first,(p/'out'/'scene_assets.c').read_bytes())
            self.assertLess(a['vram_word_ranges']['bg'][1],a['vram_word_ranges']['sprites'][0])
    def test_racing_asset_build(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);scene_pack.demo('racing',p)
            a=scene_pack.pack(p/'background.png',p/'sprites.png',p/'out')
            self.assertGreater(a['unique_tiles'],10)
            self.assertEqual(a['sprite_frames'],4)
    def test_reject_dimensions_and_palette(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);scene_pack.demo('shmup',p)
            b=p/'background.png'; sprite=p/'sprites.png'
            Image.new('RGB',(240,224)).save(b)
            with self.assertRaisesRegex(ValueError,'256x224'):
                scene_pack.pack(b,sprite,p/'out')
            Image.new('RGB',(256,224),(255,0,255)).save(b)
            with self.assertRaisesRegex(ValueError,'fixed 16-color palette'):
                scene_pack.pack(b,sprite,p/'out')
            scene_pack.demo('shmup',p)
            Image.new('RGBA',(64,15)).save(sprite)
            with self.assertRaisesRegex(ValueError,'64x16'):
                scene_pack.pack(b,sprite,p/'out')
    def test_invalid_opaque_zero(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);scene_pack.demo('shmup',p)
            atlas=Image.open(p/'sprites.png').convert('RGBA')
            atlas.putpixel((0,0),(*scene_pack.RGB[0],255));atlas.save(p/'sprites.png')
            with self.assertRaisesRegex(ValueError,'reserved transparent'):
                scene_pack.pack(p/'background.png',p/'sprites.png',p/'out')
if __name__=='__main__':unittest.main()
