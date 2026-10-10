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
    def test_duplicate_and_malformed_raw_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'raw.txt'
            f.write_text('0 100\n1a3 99\n')
            self.assertEqual(c.read_profile(f),{0:100,0x1a3:99})
            for raw in ('0 100\n0 120\n','100 BAD\n','ffffff 2\n','20 0\n','', '0 2 3\n'):
                f.write_text(raw)
                with self.assertRaises(ValueError):c.read_profile(f)
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
        missing=c.check_budget(r,{'segments':{'turn':{'max_ticks_per_frame_by_symbol':{'nonexistent_render':100}}}})
        self.assertEqual(missing['result'],'failed')
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
