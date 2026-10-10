"""Exact legacy shader equivalence and generated paired-BAT texture audit."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sys.path.insert(0,str(ROOT/'tools'))
import gen_wall_pairs as g
import verify_wall_pairs as reference
import wall_equivalence as identical

class WallPairTests(unittest.TestCase):
    def test_generated_rom_table_is_reproducible(self):
        self.assertEqual((ROOT/'src/wall_pairs.h').read_text(),g.generate())
    def test_every_material_depth_orientation_and_phase(self):
        self.assertEqual(reference.verify(),3*32*2*8*16)
    def test_both_texels_are_independent(self):
        # If both nibbles are accidentally copied from one sample,
        # the "two pixels in one BAT word" optimization loses half the texture.
        self.assertTrue(any(g.pair(style,u,v)>>4 != (g.pair(style,u,v)&15)
                            for style in range(5) for u in range(8) for v in range(16)))
    def test_all_colour_indices_within_vce_palette(self):
        for style in range(5):
            for u in range(8):
                for v in range(16):
                    value=g.pair(style,u,v)
                    self.assertTrue(0<=value<=255)
                    self.assertTrue(0<=value>>4<=15 and 0<=value&15<=15)
    def test_image_comparator_rejects_inaccurate_pixels(self):
        from tempfile import TemporaryDirectory
        from PIL import Image
        with TemporaryDirectory() as t:
            a=Path(t)/'a.png';b=Path(t)/'b.png'
            Image.new('RGB',(560,242),(30,40,50)).save(a)
            Image.new('RGB',(560,242),(30,40,50)).save(b)
            self.assertTrue(identical.compare_pixels(a,b)['matched'])
            im=Image.open(b).convert('RGB');im.putpixel((90,40),(31,40,50));im.save(b)
            with self.assertRaisesRegex(ValueError,'bitmap changed'):
                identical.compare_pixels(a,b)
            Image.new('RGB',(500,242),(30,40,50)).save(b)
            with self.assertRaisesRegex(ValueError,'560x242'):
                identical.compare_pixels(a,b)

    def test_shader_has_multiple_distance_bands(self):
        self.assertNotEqual(g.pair(0,5,5),g.pair(1,5,5))
        self.assertNotEqual(g.pair(2,2,2),g.pair(3,2,2))

if __name__=='__main__':unittest.main()
