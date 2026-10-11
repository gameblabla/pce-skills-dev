"""Generated HuC6280 wall microcode: exact texture math and honest evidence."""
import sys
from pathlib import Path
import unittest

PROJECT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sys.path.insert(0,str(PROJECT/'tools'))
import gen_wall_codegen as g
import compare_codegen as bench

class WallMicrocodeTests(unittest.TestCase):
    def test_generated_microcode_deterministic(self):
        g.validate()
        self.assertEqual((PROJECT/'src/wall_codegen.S').read_text(),g.generate())
        asm=g.generate()
        self.assertIn('lda ray_codegen_pixels+',asm)
        self.assertIn('and #$0f',asm)
        self.assertIn('and #$f0',asm)
        self.assertIn('ora ray_codegen_low_nibble',asm)
        self.assertNotRegex(asm, r'ora ray_codegen_pixels\+')
        self.assertIn('st2 #$f2',asm)
        self.assertIn('jmp (ray_codegen_target)',asm)
        self.assertIn('.size ray_codegen_h116_s0',asm)
        self.assertEqual(asm.count('    jmp .Ldone'),sum(h//8 for h in set(g.HEIGHTS)))
        self.assertIn('.word ray_codegen_h116_s0',asm)

    def test_scaled_texture_edges_and_variants(self):
        self.assertEqual(len(g.HEIGHTS),33)
        self.assertEqual(len(set(g.HEIGHTS)),23)
        for height in set(g.HEIGHTS):
            self.assertEqual(g.texture_v(height,0),0)
            self.assertLessEqual(g.texture_v(height,height-1),15)
        self.assertEqual(g.texture_v(116,115),15)

    def test_bounded_irq_critical_section(self):
        src=(PROJECT/'src/main.c').read_text()
        self.assertIn('ray_codegen_emit();',src)
        self.assertIn('pce_cpu_irq_disable();',src)
        self.assertIn('pce_cpu_irq_enable();',src)
        self.assertIn('ray_codegen_words=',src)
        self.assertIn('ray_backdrop_word(yy,pair)',src)
        self.assertIn('pce_memop((void*)IO_VDC_DATA,staged_words+offset+done',src)
        self.assertIn('if(n>8u)n=8u;',src)
        self.assertIn('yy>=tl && yy<el',src)
        self.assertIn('yy>=tr && yy<er',src)
        self.assertIn('(yy-tl)&7u',src)
        self.assertIn('RAY_WALL_CODEGEN=0', (PROJECT/'Makefile').read_text())

    def example(self):
        result=[]
        for name in ('idle','turn-right','walk','turn-left','settle','quiet'):
            result.append({'segment':name,'emulator_frames':90,'game_updates':40,
                           'dirty_views':5 if name in ('turn-right','walk','turn-left') else 0,
                           'vram_words':1000 if name in ('turn-right','walk','turn-left') else 0,
                           'generated_words':512 if name in ('turn-right','walk','turn-left') else 0})
        return {'scenario':result,'totals':{'turning_views_per_second':3.333}}

    def test_benchmark_rejects_fabricated_generated_writes(self):
        a=self.example();b=self.example()
        self.assertEqual(bench.compare(a,b)['codegen_words'],1536)
        b['scenario'][1]['generated_words']=511
        with self.assertRaisesRegex(ValueError,'eight-word'):bench.compare(a,b)
        b['scenario'][1]['generated_words']=0
        b['scenario'][2]['generated_words']=0
        b['scenario'][3]['generated_words']=0
        with self.assertRaisesRegex(ValueError,'never ran'):bench.compare(a,b)

    def test_benchmark_rejects_regressions(self):
        a=self.example();b=self.example();b['totals']['turning_views_per_second']=1
        with self.assertRaisesRegex(ValueError,'regresses'):bench.compare(a,b)

if __name__=='__main__':unittest.main()
