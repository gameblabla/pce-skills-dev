"""Generated artwork exemptions require byte-for-byte provenanced data."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import model_guard

class VNGuardTests(unittest.TestCase):
    def test_generated_asset_provenance_and_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'src').mkdir();(p/'assets').mkdir()
            import hashlib
            sources={}
            for name in ('background.png','mouth_closed.png','mouth_open.png'):
                content=b'valid-placeholder';(p/'assets'/name).write_bytes(content)
                sources[name]=hashlib.sha256(content).hexdigest()
            raw='#include "vn_assets.h"\nconst unsigned char A[]={'+','.join('0xFF' for _ in range(11000))+'};'
            file=p/'src/vn_assets.c';file.write_text(raw)
            meta={'format':'pce-vn-pack-v1','source_hashes':sources,
                  'generated_c_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
            (p/'src/manifest.json').write_text(json.dumps(meta))
            self.assertEqual(model_guard.scan(p),[])
            file.write_text(raw+'  //tampered')
            self.assertEqual(model_guard.scan(p)[0]['code'],'large-inline-assets')
            file.write_text(raw)
            (p/'assets/mouth_open.png').write_bytes(b'changed')
            self.assertEqual(model_guard.scan(p)[0]['code'],'large-inline-assets')
if __name__=='__main__':unittest.main()
