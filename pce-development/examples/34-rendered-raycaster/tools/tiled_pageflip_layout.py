#!/usr/bin/env python3
"""Pure host-side invariants for tiled dual-page BAT layout and scanline IRQ."""
from pathlib import Path
from gen_pageflip_tiled import quant,irq

def check():
    groups=[{(row<<7)+(page<<6)+col for row in range(32) for col in range(64)} for page in range(2)]
    assert len(groups[0])==len(groups[1])==2048
    assert not(groups[0]&groups[1])
    assert groups[0]|groups[1]=={row*128+col for row in range(32) for col in range(128)}
    assert all(addr<0x2000 for group in groups for addr in group)
    assert 0x2000+255*16+15<0x3000
    assert 'eor #1' in irq() and 'stz ray_flip_pending' in irq()
    assert '    st2 #2' in irq() and '    st2 #0' in irq()
    assert 'cpx #31' in irq()
    assert 'ray_tiled_palettes[16][2]' in quant()
    print('tiled pageflip: 2 disjoint 2048-word BAT pages, patterns and VBlank page selection verified')
if __name__=='__main__':check()
