"""Test HuC6280 narrow arithmetic on the host, without needing LLVM-MOS."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]/'libcommon'

class FastmathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        path=Path(cls.temp.name)/'libfastmath.so'
        cc=shutil.which('cc')
        if not cc:raise unittest.SkipTest('host C compiler missing')
        subprocess.run([cc,'-shared','-fPIC','-O2','-std=c11','-I'+str(ROOT/'include'),
                        str(ROOT/'src/fastmath.c'),str(ROOT/'src/mode7.c'),str(ROOT/'src/circle.c'),
                        '-o',str(path)],check=True)
        cls.dylib=ctypes.CDLL(str(path))
        for symbol,argtypes,restype in (
            ('pce_mul8',[ctypes.c_uint8,ctypes.c_uint8],ctypes.c_uint16),
            ('pce_mul_s8u8',[ctypes.c_int8,ctypes.c_uint8],ctypes.c_int16),
            ('pce_div16by8',[ctypes.c_uint16,ctypes.c_uint8],ctypes.c_uint16),
            ('pce_q6',[ctypes.c_int16],ctypes.c_int16),
            ('pce_shift_towards_zero',[ctypes.c_int16,ctypes.c_uint8],ctypes.c_int16),
            ('pce_mode7_axis',[ctypes.c_uint8,ctypes.c_uint8],ctypes.c_int16),
            ('pce_circle_radius',[ctypes.c_uint8],ctypes.c_int8)):
            fn=getattr(cls.dylib,symbol);fn.argtypes=argtypes;fn.restype=restype

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_every_unsigned_8_product(self):
        fn=self.dylib.pce_mul8
        for a in range(256):
            for b in range(256):
                self.assertEqual(fn(a,b),a*b)

    def test_signed_8_product_boundaries(self):
        fn=self.dylib.pce_mul_s8u8
        for a in (-128,-127,-65,-9,-1,0,1,7,63,127):
            for b in range(256):self.assertEqual(fn(a,b),a*b)

    def test_division_reference(self):
        fn=self.dylib.pce_div16by8
        for a in (0,1,255,256,257,999,4095,16383,32767,65535):
            for b in range(1,256):self.assertEqual(fn(a,b),a//b)
        for a in range(0,65536,127):
            for b in (1,3,7,33,127,255):self.assertEqual(fn(a,b),a//b)
        self.assertEqual(fn(65535,0),65535)

    def test_signed_shifts(self):
        fn=self.dylib.pce_shift_towards_zero
        for v in (-32768,-32000,-1025,-127,-63,-1,0,1,63,127,1025,32767):
            for bits in range(8):
                expect=(abs(v)>>bits)*(1 if v>=0 else -1)
                self.assertEqual(fn(v,bits),expect)
                if bits==6:self.assertEqual(self.dylib.pce_q6(v),expect)

    def test_mode7_table_matches_reference(self):
        sine=(0,49,90,117,127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49)
        fn=self.dylib.pce_mode7_axis
        for angle in range(16):
            for row in range(93):
                expected=sine[angle]*(1408//(row+8))
                self.assertEqual(fn(angle,row),expected)
        self.assertEqual(fn(7,99),0)

    def test_circle_table_is_exact(self):
        fn=self.dylib.pce_circle_radius
        for dy in range(65):
            got=fn(dy)
            expected=max((x for x in range(64) if x*x+dy*dy<1600),default=-1)
            self.assertEqual(got,expected)

if __name__=='__main__':unittest.main()
