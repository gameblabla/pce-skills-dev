"""Source-sheet reproducibility and dual-layer SGX budget boundaries."""
import sys,unittest,json
from pathlib import Path
from PIL import Image
PROJECT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sys.path.insert(0,str(PROJECT/'tools'))
import gen_texture_sheet as pce
import sgx_texture_plan as sgx

class TextureSheetTests(unittest.TestCase):
    def test_sheets_stay_vendored_and_deterministic(self):
        self.assertEqual(Image.open(PROJECT/'assets/wolftextures16.png').size,(224,32))
        self.assertEqual(Image.open(PROJECT/'assets/wolftextures256.png').size,(224,32))
        header,palette,manifest=pce.generate()
        self.assertEqual((PROJECT/'src/sheet_pairs.h').read_text(),header)
        self.assertEqual((PROJECT/'src/sheet_palette.h').read_text(),palette)
        self.assertEqual((PROJECT/'assets/texture_manifest.json').read_text(),manifest)
        self.assertEqual(json.loads(manifest)['source_pce_unique_colours'],15)

    def test_16_colours_and_exact_paired_indices(self):
        pairs=pce.converted();self.assertEqual(len(pairs),14)
        for style in range(14):
            for u in range(16):
                self.assertEqual(len(pairs[style][u]),16)
                for v in range(16):
                    packed=pairs[style][u][v]
                    self.assertLess(packed>>4,16)
                    self.assertLess(packed&15,16)
                    self.assertEqual(packed&15,pairs[style][(u+1)&15][v]>>4)

    def test_sgx_plan_validates_both_pixel_layers(self):
        header,report,preview=sgx.generate()
        self.assertEqual((PROJECT/'src/sgx_texture_planes.h').read_text(),header)
        self.assertEqual((PROJECT/'assets/sgx_dual_plan.json').read_text(),report)
        self.assertEqual(preview.tobytes(),Image.open(PROJECT/'assets/sgx_dual_preview.png').convert('RGB').tobytes())
        m=json.loads(report)
        self.assertFalse(m['runtime_verified'])
        self.assertEqual(m['source_unique_colours'],105)
        self.assertEqual(m['total_rom_plane_bytes'],7168)
        for material in m['per_material']:
            self.assertLessEqual(material['vdc_a_colors'],15)
            self.assertLessEqual(material['vdc_b_colors'],15)
            self.assertEqual(material['packed_pair_bytes_per_vdc'],512)

if __name__=='__main__':unittest.main()
