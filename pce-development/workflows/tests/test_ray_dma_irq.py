"""Verify the DMA ISR leaves timing-critical raster programming ahead of its flag handling."""
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[2] / 'examples/34-rendered-raycaster'


class DMAIRQTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asm = (SRC / 'src/bat_dma_irq.S').read_text()
        cls.main = (SRC / 'src/main.c').read_text()
        cls.mk = (SRC / 'Makefile').read_text()

    def test_flag_set_after_scroll_registers(self):
        asm = self.asm
        self.assertEqual(asm.count('lda $0000'), 1, 'read hardware status just once per IRQ')
        self.assertLess(asm.index('st0 #8\n    lda irq_byr_low,x'), asm.index('inc ray_dma_completed'))
        self.assertLess(asm.index('st0 #6\n    lda irq_rcr_low,x'), asm.index('inc ray_dma_completed'))
        self.assertLess(asm.index('.Ldone:'), asm.index('inc ray_dma_completed'))

    def test_dma_uses_interrupt_not_polling(self):
        main = self.main
        self.assertIn('pce_vdc_dma_start(VDC_DMA_IRQ_DONE', main)
        self.assertIn('while(!ray_dma_completed)', main)
        self.assertIn('while(!pce_vdc_dma_finished())', main, 'leave baseline path reproducible')
        self.assertIn('for(uint8_t piece=0u;piece<2u;++piece)', main)
        self.assertIn('4096u', main)

    def test_opt_in_target_preserves_default(self):
        self.assertIn('vram-buffer-irq-rom:', self.mk)
        self.assertIn('-DRAY_VRAM_IRQ_DMA=1', self.mk)
        self.assertIn('vram-buffer-irq-compare:', self.mk)
        self.assertIn('vram-buffer-irq-stress:', self.mk)
        self.assertNotIn('RAY_VRAM_IRQ_DMA=1', self.mk.split('$(OUT):', 1)[1].split('$(BASELINE_ROM):', 1)[0] if '$(BASELINE_ROM):' in self.mk else self.mk.split('$(OUT):', 1)[1].split('.PHONY:',1)[0])


if __name__ == '__main__':
    unittest.main()
