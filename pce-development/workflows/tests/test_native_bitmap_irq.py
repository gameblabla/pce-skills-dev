"""Native BAT IRQ regression rules; no emulator or compiler required."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ASM=ROOT/'libcommon/src/bat_bitmap_irq.S'
RAY=ROOT/'examples/34-rendered-raycaster'
MICRO=ROOT/'examples/micro'

class NativeBitmapIRQTests(unittest.TestCase):
    def test_shared_and_exportable_irq_are_identical(self):
        self.assertEqual(ASM.read_bytes(),(RAY/'src/bat_bitmap_irq.S').read_bytes())

    def test_symbol_range_and_unsafe_optimizations_are_forbidden(self):
        code=ASM.read_text()
        for required in ('.type irq_vdc,@function','.size irq_vdc, .-irq_vdc',
                         'pha','phx','phy','ply','plx','pla','rti',
                         'st0 #7','st0 #8','st0 #6','bat_phase','bat_source_y',
                         'inc bat_frames','cmp #223'):
            self.assertIn(required,code)
        self.assertNotIn('sei',code)
        self.assertIn('cmp #64',code)
        self.assertNotIn('bat_irq_count',code)

    def test_scroll_high_word_borrow_at_every_32_rows(self):
        code=ASM.read_text()
        # The previous native IRQ tested (y & 63) == 0, overlooking y=32
        # and y=96. Those errors appeared as two dark Mode 7 sky stripes.
        self.assertIn('and #$1f\n    bne .Lno_borrow\n    dex',code)
        self.assertNotIn('beq .Lhigh_ff',code)
        for y in range(128):
            native_hi=(((y>>5)&1) - (1 if (y&31)==0 else 0))&0xff
            native_lo=((y&63)*8-1)&0xff
            reference=((y&63)*8-1)&0xffff
            self.assertEqual((native_hi<<8)|native_lo,reference, f'row {y}')

    def test_opt_in_only_for_graphical_bitmap_examples(self):
        self.assertIn('NATIVE_BITMAP_IRQ := 1',(MICRO/'86-mode7-bitmap-floor/Makefile').read_text())
        self.assertNotIn('NATIVE_BITMAP_IRQ', (MICRO/'03-psg-tone/Makefile').read_text())
        make=(RAY/'Makefile').read_text()
        self.assertIn('-DBAT_BITMAP_NATIVE_IRQ',make)
        self.assertIn('src/bat_bitmap_irq.S',make)
        common=(MICRO/'common.mk').read_text()
        self.assertIn('ifeq ($(NATIVE_BITMAP_IRQ),1)',common)
        self.assertIn('$(NATIVE_BITMAP_SRC)',common)
        h=(MICRO/'bat_bitmap.h').read_text()
        self.assertIn('#ifndef BAT_BITMAP_NATIVE_IRQ',h)
        self.assertIn('extern void irq_vdc(void);',h)

    def test_each_scanline_has_a_source_row_and_second_bat_half(self):
        y=phase=0
        seen=[]
        for line in range(1,224):
            phase+=4
            if phase>=7:
                phase-=7
                y+=1
            seen.append(y)
        self.assertEqual(len(seen),223)
        self.assertEqual(max(seen),127)
        self.assertEqual(min(seen),0)
        self.assertIn(64,seen)
        self.assertTrue(all(b-a in (0,1) for a,b in zip(seen,seen[1:])))
        self.assertLess(max(seen.count(row) for row in range(128)),3)

if __name__=='__main__':unittest.main()
