import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('perf_compare',ROOT/'perf_compare.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class CoverageSafetyTests(unittest.TestCase):
    def test_rejects_noncoverage_data_and_empty_frames(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'fake.json'
            f.write_text(json.dumps({'format':'fake','frames':3,'total_instructions':90}))
            with self.assertRaises(ValueError):p.coverage(f)
            f.write_text(json.dumps({'format':'mednafen-pce-logical-pc-coverage-v1','frames':0,'total_instructions':90}))
            with self.assertRaises(ValueError):p.coverage(f)
    def test_counts_not_mislabeled_as_cycles(self):
        self.assertIn('not HuC6280 cycles',p.__doc__)
if __name__=='__main__':unittest.main()
