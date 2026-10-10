"""Cycle profiler tests require neither LLVM-MOS nor the headless emulator."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/'cycle_profile.py'
spec=importlib.util.spec_from_file_location('cycle_profile',FILE)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class ProfileTests(unittest.TestCase):
    def test_physical_rom_symbols(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'link.mlb'
            f.write_text('PcePrgRom:200-207:main\nPcePrgRom:204-205:hot\nPceWorkRam:210-211:frame\n')
            labels=c.rom_labels(f)
            names,unknown=c.mapped_names(labels,{0x200:3,0x204:17,0x210:19})
            self.assertEqual(names,{'main':3,'hot':17,'<unmapped>':19})
            self.assertEqual(unknown,19)
            self.assertEqual(c.find_ram_symbol(f,'frame'),(0x2210,2))
            with self.assertRaisesRegex(ValueError,'cannot find'):c.find_ram_symbol(f,'bogus')
            # A one-byte IRQ label is *not* evidence of a one-byte handler.
            # Require assembly .type/.size so costly instructions are counted.
            f.write_text('PcePrgRom:24:irq_vdc\nPcePrgRom:50-70:main\n')
            with self.assertRaisesRegex(ValueError,'no ROM span'):c.rom_labels(f)
            f.write_text('PcePrgRom:24-b3:irq_vdc\nPcePrgRom:50-70:main\n')
            self.assertEqual(c.rom_labels(f)[0],(0x24,0xb3,'irq_vdc'))
    def test_sdk_block_transfer_uses_verified_linker_section(self):
        with tempfile.TemporaryDirectory() as d:
            mlb=Path(d)/'x.mlb'
            mp=Path(d)/'x.pce.map'
            mlb.write_text('PcePrgRom:b8:pce_memop\nPcePrgRom:d4:nmi\n')
            mp.write_text('    e0b8 e0b8 1c 1 libc.a:(.text.pce_memop)\n')
            self.assertEqual(c.rom_labels(mlb),[(0xb8,0xb8,'pce_memop'),(0xd4,0xd4,'nmi')])
            self.assertIn((0xb8,0xd3,'pce_memop'),c.rom_labels(mlb,mp))
            names,unmapped=c.mapped_names(c.rom_labels(mlb,mp),{0xc6:90,0xd4:30})
            self.assertEqual(names['pce_memop'],90)
            self.assertEqual(unmapped,0)
            for start,size in [('e0b9','1c'),('e0b8','0'),('e0b8','400')]:
                mp.write_text(f'    {start} {start} {size} 1 libc.a:(.text.pce_memop)\n')
                with self.assertRaises(ValueError):c.rom_labels(mlb,mp)
            mp.write_text('    e0b8 e0b8 1d 1 libc.a:(.text.pce_memop)\n')
            with self.assertRaisesRegex(ValueError,'overlaps'):c.rom_labels(mlb,mp)

    def test_duplicate_and_malformed_raw_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'raw.txt'
            f.write_text('0 100\n1a3 99\n')
            self.assertEqual(c.read_profile(f),{0:100,0x1a3:99})
            for raw in ('0 100\n0 120\n','100 BAD\n','ffffff 2\n','20 0\n','', '0 2 3\n'):
                f.write_text(raw)
                with self.assertRaises(ValueError):c.read_profile(f)
    def test_native_dump_metadata_matches_serialized_histogram(self):
        parsed={0x100:100,0x210:200}
        c.validate_native_dump({'ok':True,'records':2,'master_ticks':300},parsed)
        c.validate_native_dump({'ok':True},parsed)  # older compatible frontend
        for bad in ({'records':3},{'master_ticks':301},
                    {'records':2.0},{'master_ticks':'300'}):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'mismatches'):
                c.validate_native_dump(bad,parsed)

    def test_categories_and_frame_sanity(self):
        frames=10
        labels=[(0x80,0xff,'main'),(0x100,0x130,'irq_vdc')]
        r=c.summarize({0x80:2000000,0x100:1500000,0x200:10000},labels,frames)
        self.assertEqual(r['master_clock_ticks'],3510000)
        self.assertEqual(r['categories']['interrupt'],1500000)
        self.assertTrue(r['attributed_pct']>99)
        with self.assertRaisesRegex(ValueError,'outside plausible'):c.summarize({0x80:123},labels,frames)
        with self.assertRaises(ValueError):c.summarize({0x80:3000000},labels,0)
    def test_scenarios_reject_unbounded_or_bogus_input(self):
        good={'warmup_frames':5,'segments':[{'name':'idle','frames':20,'buttons':['right']}]}
        self.assertEqual(c.validate_scenario(good),good)
        for bad in (
            {'segments':[]},
            {'segments':[{'name':'Bad/../../', 'frames':20}]},
            {'segments':[{'name':'a','frames':1}]},
            {'segments':[{'name':'a','frames':20,'buttons':['Z']}]},
            {'segments':[{'name':'a','frames':20},{'name':'a','frames':20}]},
            {'segments':[{'name':'a','frames':20}], 'progress':{'kind':'g2tr','ram_symbol':'../../foo'}},
            {'segments':[{'name':'a','frames':20}], 'progress':{'kind':'counter','ram_symbol':'frame','width':4}},
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):c.validate_scenario(bad)
    def test_g2tr_progress_reads_complete_record(self):
        import struct
        class MockRPC:
            def call(self,op,*args):
                self.op=op;self.args=args;return {'hex':raw.hex()}
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'p.mlb';f.write_text('PceWorkRam:20b-28a:pce_genre_trace\n')
            raw=bytearray(128)
            raw[:4]=b'G2TR';raw[4]=2;raw[8:12]=(23).to_bytes(4,'little');raw[14:16]=(3).to_bytes(2,'little') # incomplete
            raw[64:68]=b'G2TR';raw[68]=2;raw[72:76]=(25).to_bytes(4,'little')
            self.assertEqual(c.read_progress(MockRPC(),f,{'kind':'g2tr','ram_symbol':'pce_genre_trace'}),25)
            raw[64:68]=b'fail'
            with self.assertRaisesRegex(ValueError,'not yet published'):c.read_progress(MockRPC(),f,{'kind':'g2tr','ram_symbol':'pce_genre_trace'})
    def test_per_routine_budget_failure(self):
        s=c.summarize({0x200:2500000,0x300:1000000},[(0x200,0x200,'irq_vdc'),(0x300,0x300,'render_slice')],10)
        s['game_updates']=4
        r={'format':'pce-master-clock-symbol-profile-v1','segments':{'turn':s}}
        fail=c.check_budget(r,{'segments':{'turn':{'min_game_updates':5,'max_ticks_per_frame_by_symbol':{'irq_vdc':200000},'max_pct_by_category':{'interrupt':50}}}})
        self.assertEqual(fail['result'],'failed');self.assertEqual(len(fail['issues']),3)
        ok=c.check_budget(r,{'segments':{'turn':{'min_game_updates':4,'max_ticks_per_frame_by_symbol':{'render_slice':110000},'max_pct_by_category':{'interrupt':80}}}})
        self.assertEqual(ok['result'],'passed')
        s['attributed_pct']=75.0
        partial=c.check_budget(r,{'segments':{'turn':{'min_attributed_pct':99}}})
        self.assertEqual(partial['result'],'failed')
        self.assertIn('only 75.00%',partial['issues'][0])
        no_transfer=c.check_budget(r,{'segments':{'turn':{'max_unmapped_ticks_per_frame':50}}})
        self.assertEqual(no_transfer['result'],'passed')
        s['unmapped_master_ticks']=800
        too_much=c.check_budget(r,{'segments':{'turn':{'max_unmapped_ticks_per_frame':70}}})
        self.assertEqual(too_much['result'],'failed')
        with self.assertRaisesRegex(ValueError,'max_unmapped_ticks_per_frame'):
            c.check_budget(r,{'segments':{'turn':{'max_unmapped_ticks_per_frame':-1}}})
        with self.assertRaisesRegex(ValueError,'min_attributed_pct'):
            c.check_budget(r,{'segments':{'turn':{'min_attributed_pct':120}}})
        missing=c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol':{'nonexistent_render':100}}}})
        self.assertEqual(missing['result'],'failed')
        # A compiler may inline column_upload into main: both symbol layouts
        # must account for the same total time without silently losing a cap.
        inline={'symbols':['render_slice','other_helper'],'max':120000}
        self.assertEqual(c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol_groups':[inline]}}})['result'],'passed')
        separated={'symbols':['render_slice','irq_vdc'],'max':120000}
        self.assertEqual(c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol_groups':[separated]}}})['result'],'failed')
        absent={'symbols':['never_a','never_b'],'max':200000}
        self.assertIn('missing all symbols',c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol_groups':[absent]}}})['issues'][0])
        for invalid in ({'symbols':[],'max':100}, {'symbols':['main','main'],'max':100},
                        {'symbols':['main'],'max':0}, {'symbols':'main','max':100}):
            with self.assertRaisesRegex(ValueError,'grouped ticks'):
                c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol_groups':[invalid]}}})
    def test_compare_does_not_claim_speedup_when_game_updates_differ(self):
        a=c.summarize({0x100:3500000},[(0x100,0x100,'main')],10)
        b=c.summarize({0x100:3500000},[(0x100,0x100,'main')],10)
        a.update(buttons=['right'],game_updates=2)
        b.update(buttons=['right'],game_updates=3)
        base={'format':'pce-master-clock-symbol-profile-v1','rom_sha256':'a','segments':{'test':a}}
        improved={'format':'pce-master-clock-symbol-profile-v1','rom_sha256':'b','segments':{'test':b}}
        result=c.diff_reports(base,improved)
        self.assertFalse(result['test']['routine_cost_comparable'])
        self.assertIsNone(result['test']['per_symbol_delta_ticks_per_frame'])
        b['game_updates']=2
        self.assertTrue(c.diff_reports(base,improved)['test']['routine_cost_comparable'])
        b['buttons']=[]
        with self.assertRaisesRegex(ValueError,'different frame count or input'):c.diff_reports(base,improved)

if __name__=='__main__':unittest.main()
