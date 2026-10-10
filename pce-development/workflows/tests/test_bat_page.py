"""Offline checks for full/atomic BAT layouts and screenshot evidence semantics."""
import importlib.util
from pathlib import Path
import sys
import unittest

R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paired_bat_plan',R/'paired_bat_plan.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
EX=R.parent/'examples/34-rendered-raycaster'
spec2=importlib.util.spec_from_file_location('atomic_present',EX/'tools/atomic_present.py')
sys.path.insert(0,str(EX/'tools'))
a=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(a)


def sample(i,page,redraws,digest=None,pending=255):
    return {'step':i,'page':page,'redraws':redraws,'pending':pending,
            'digest':digest or chr(97+i%3)*64}

class PairedBatPlanTests(unittest.TestCase):
    def test_full_uses_every_bat_word_once(self):
        p=b.plan('full')
        self.assertEqual(p['logical_pixels'],[128,128])
        self.assertEqual(p['bytes_per_page'],16384)
        self.assertEqual(p['batches_per_complete_image'],16)
        self.assertEqual(p['presentation'],'progressive-bat')
    def test_atomic_uses_two_disjoint_pages(self):
        p=b.plan('atomic')
        self.assertEqual(p['logical_pixels'],[128,64])
        self.assertEqual(p['bytes_per_page'],8192)
        self.assertEqual(p['batches_per_complete_image'],8)
        self.assertEqual(p['presentation'],'vblank-atomic-bxr-swap')
        self.assertEqual(b.word_address(0,0,mode='atomic',page=1),64)
        self.assertEqual(b.word_address(63,63,mode='atomic',page=1),8191)
        self.assertEqual(b.word_address(64,0,mode='full'),64)
    def test_rejects_writing_other_page_in_full_mode(self):
        for kw in ({'mode':'full','page':1},{'mode':'atomic','page':2}):
            with self.assertRaises(ValueError):b.word_address(1,0,**kw)
    def test_bad_rows_columns_batches_modes(self):
        for yy,xx in ((-1,0),(0,64),(64,1)):
            with self.assertRaises(ValueError):b.word_address(yy,xx,mode='atomic')
        for md,sz in (('full',16),('atomic',12),('notreal',8)):
            with self.assertRaises(ValueError):b.plan(md,batch_rows=sz)
    def test_native_irq_selection_and_build_variant(self):
        code=(EX/'src/bat_bitmap_irq.S').read_text()
        self.assertIn('bat_display_page',code)
        self.assertIn('bat_ready_page',code)
        self.assertIn('adc #2',code)
        mk=(EX/'Makefile').read_text()
        self.assertIn('ATOMIC_FLAGS',mk)
        self.assertIn('atomic-bitmap-test',mk)
        self.assertNotIn('PCE_FLAGS += -DBAT_BITMAP_NATIVE_IRQ -DRAY_DOUBLE_BUFFER=1',mk)

class AtomicProofTests(unittest.TestCase):
    def good(self):
        return [sample(0,0,4,'a'*64),sample(1,0,4,'a'*64),
                sample(2,1,5,'b'*64),sample(3,1,5,'b'*64),
                sample(4,0,6,'c'*64),sample(5,0,6,'c'*64),
                sample(6,1,7,'d'*64),sample(7,1,7,'d'*64)]
    def test_normal_unchanged_when_no_swap(self):
        self.assertEqual(a.check_atomic_samples(self.good())['swaps'],3)
    def test_screenshot_lag_one_sample_allowed(self):
        samples=self.good()
        samples[2]['digest']='a'*64
        samples[3]['digest']='b'*64
        self.assertEqual(a.check_atomic_samples(samples)['one_sample_capture_lags'],1)
    def test_tearing_after_bounded_capture_lag_rejected(self):
        samples=self.good()
        samples[1]['digest']='e'*64
        with self.assertRaisesRegex(ValueError,'TEARING'):a.check_atomic_samples(samples)
    def test_swap_without_page_change_rejected(self):
        samples=self.good()
        samples[4]['page']=1
        with self.assertRaisesRegex(ValueError,'toggle'):a.check_atomic_samples(samples)
    def test_pending_front_page_rejected(self):
        samples=self.good()
        samples[4]['pending']=0
        with self.assertRaisesRegex(ValueError,'queued back page'):a.check_atomic_samples(samples)
    def test_fake_progress_rejected(self):
        samples=self.good()
        samples[4]['redraws']=5
        with self.assertRaises(ValueError):a.check_atomic_samples(samples)
if __name__=='__main__':unittest.main()
