"""Negative tests for the 8/16-bit-only target code policy."""
import importlib.util
from pathlib import Path
import json
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('arith_guard',ROOT/'arith_guard.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class ArithmeticGateTests(unittest.TestCase):
    def test_real_sources_respect_frozen_baseline(self):
        self.assertTrue(a.scan(ROOT.parent/'examples')['ok'])
        self.assertTrue(a.scan(ROOT.parent/'libcommon')['ok'])

    def test_new_widths_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);(path/'main.c').write_text('''#include <stdint.h>\nuint64_t bad;\nint32_t bad2;\nlong bad3;\ndouble bad4;\nuint16_t fine;\n''')
            issues=a.scan(path)['issues']
            self.assertEqual(len(issues),4)

    def test_quotes_and_comments_are_not_code(self):
        self.assertEqual(a.forbidden_lines('''/* int64_t z; */\n"int32_t";\n// long foo\nuint16_t x;\n'''),[])

    def test_existing_line_cannot_be_duplicated(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);(path/'main.c').write_text('int32_t age;\nint32_t age;\n')
            # use repo-relative path form only within a temporary manifest
            legacy=path/'legacy.json'
            legacy.write_text(json.dumps({'exceptions':{'main.c':{'line_hash_counts':{a.line_hash('int32_t age;'):1}}}}))
            issues=a.scan(path,legacy)['issues']
            self.assertEqual(len(issues),1)

    def test_makefile_linking_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'Makefile').write_text('LINK_FLAGS := -lm -lgcc\n')
            self.assertFalse(a.scan(p)['ok'])

    def test_strict_elf_catches_bad_helpers(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);elf=p/'fake.elf';elf.write_bytes(b'fake')
            nm=p/'nm';nm.write_text('#!/bin/sh\necho "0000e000 t __mulhi3"\necho "0000e020 t __divsi3"\n');nm.chmod(0o755)
            report=a.elf_scan(elf,str(nm))
            self.assertEqual(report['software_math'],['__divsi3','__mulhi3'])
            nm.write_text('#!/bin/sh\necho "0000e000 t pce_mul8"\n')
            self.assertTrue(a.elf_scan(elf,str(nm))['ok'])

if __name__=='__main__':unittest.main()
