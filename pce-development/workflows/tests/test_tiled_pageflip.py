"""Offline geometry and reproducibility checks for experimental BAT page selection."""
import sys
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'examples'/'34-rendered-raycaster'
sys.path.insert(0,str(BASE/'tools'))
import gen_pageflip_tiled as tiled

class TiledPageFlipTests(unittest.TestCase):
    def test_no_visible_page_overlap(self):
        pages=[{(row<<7)+(page<<6)+col for row in range(32) for col in range(64)}
               for page in (0,1)]
        self.assertEqual((len(pages[0]),len(pages[1])),(2048,2048))
        self.assertFalse(pages[0].intersection(pages[1]))
        self.assertTrue(all(v<0x2000 for page in pages for v in page))
        self.assertLess(0x2000+256*16,0x3001)

    def test_glyph_palette_and_scroll_schedule(self):
        s=tiled.quant()
        self.assertIn('ray_tiled_palettes[16][2]',s)
        self.assertEqual(len(tiled.PAIRS),16)
        self.assertEqual(len(set(tiled.PAIRS)),16)
        asm=tiled.irq()
        self.assertIn('    eor #1',asm)
        self.assertIn('    stz ray_flip_pending',asm)
        self.assertIn('    cpx #31',asm)
        self.assertIn('    st2 #2',asm)
        self.assertIn('    st2 #0',asm)
        # RCR=0x41+7, then one skipped scanline every 7 physical lines.
        self.assertIn('    st1 #$48',asm)

    def test_generated_sources_and_no_full_bat_dma_copy(self):
        self.assertEqual((BASE/'src'/'pageflip_tiled_quant.h').read_text(),tiled.quant())
        self.assertEqual((BASE/'src'/'bat_pageflip_tiled_irq.S').read_text(),tiled.irq())
        source=(BASE/'src'/'pageflip_tiled.c').read_text()
        self.assertIn('while(ray_flip_pending)',source)
        self.assertIn('flip_next_group==64u',source)
        self.assertNotIn('pce_vdc_dma_start(',source)

if __name__=='__main__':unittest.main()
