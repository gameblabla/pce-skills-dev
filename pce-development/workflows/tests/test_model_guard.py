"""Regression tests from *patterns* in four local-AI sessions (no transcripts bundled)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

guard=load('model_guard');packer=load('assetpack')
SAMPLE=ROOT/'specs/pce-level.json'

class ModelGuardTests(unittest.TestCase):
    def test_clean_baseline(self):
        for name in ('26-platformer-starter','27-platformer-racer','28-generated-level'):
            self.assertEqual([],guard.scan(ROOT.parent/'examples'/name))
    def test_invalid_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir()
            (src/'main.c').write_text('int n = KEY_A + KEY_START + VDC_SPRITE_HFLIP;\n')
            findings=guard.scan(tmp)
            self.assertEqual(len(findings),3)
            self.assertTrue(any('KEY_1' in x['fix'] for x in findings))
    def test_comments_strings_not_false_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'main.c'
            p.write_text('/* KEY_START */\nconst char*s="KEY_A"; // VDC_SPRITE_HFLIP\n')
            self.assertFalse(guard.scan(tmp))
    def test_redefined_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'main.h').write_text('#define KEY_RIGHT 0x08\n')
            self.assertEqual(guard.scan(tmp)[0]['code'],'redefined-joypad')
    def test_sdk_log_categorization(self):
        examples={
          'undeclared identifier \'KEY_A\'':'sdk-key',
          'undeclared identifier \'VDC_SPRITE_HFLIP\'':'sdk-sprite',
          'error: excess elements in array initializer':'array-count',
          "ld.lld: error: section '.rodata' will not fit in region 'rom_bank0'":'rom-overflow',
          'error: unused variable \'minute\' [-Werror,-Wunused-variable]':'unused-werror',
          'unknown rpc command':'rpc-unsupported',
          'timeout: failed to run command':'emulator-timeout',
        }
        for line,expected in examples.items():
            with self.subTest(line=line):
                self.assertIn(expected,[x['code'] for x in guard.diagnose(line)])
    def test_unclassified_no_fake_fix(self):
        self.assertEqual(guard.diagnose('unusual fault')[0]['code'],'unclassified')
    def test_hucard_not_cd(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'evidence.json'
            path.write_text(json.dumps({'target':'supercd','artifact':'game.pce',
                'evidence':{'compiled':True,'neutral_emulator':True,'input_scenario':True,'visual_review':True,'real_cd_boot':False}}))
            result=guard.evidence(path)
            self.assertFalse(result['complete'])
            self.assertIn('real_cd_boot',result['missing'])
            self.assertTrue(any('disc image' in x for x in result['missing']))
    def test_compiled_does_not_mean_playable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'one.json';p.write_text(json.dumps({'target':'hucard','evidence':{'compiled':True}}))
            self.assertFalse(guard.evidence(p)['complete'])
            self.assertIn('input_scenario',guard.evidence(p)['missing'])
    def test_complete_claim_self_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'one.json';p.write_text(json.dumps({'target':'hucard','evidence':{
                'compiled':True,'neutral_emulator':True,'input_scenario':True,'visual_review':True}}))
            self.assertTrue(guard.evidence(p)['complete'])
            self.assertIn('self-reported',guard.evidence(p)['warning'])
    def test_invalid_target_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'one.json';p.write_text(json.dumps({'target':'cd','evidence':{}}))
            with self.assertRaises(ValueError):guard.evidence(p)

class AssetPackTests(unittest.TestCase):
    def fixture(self):return json.loads(SAMPLE.read_text())
    def test_valid_level(self):
        c=packer.compiled(packer.load(SAMPLE))
        self.assertEqual((c['width'],c['height']),(64,28))
        self.assertEqual(len(c['patterns']),192)
        self.assertEqual(len(c['bat']),64*28)
    def test_encode_plane_layout(self):
        p=packer.encode_pattern(['f0000000']*8)
        self.assertEqual(len(p),32)
        self.assertEqual(p[:2],[128,128])
        self.assertEqual(p[16:18],[128,128])
    def bad(self,mutate):
        v=self.fixture();mutate(v)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.json';p.write_text(json.dumps(v))
            with self.assertRaises(ValueError):packer.load(p)
    def test_mismatched_row(self):self.bad(lambda j:j['map'].__setitem__(8,'x'))
    def test_undefined_glyph(self):self.bad(lambda j:j['map'].__setitem__(8,'?'*64))
    def test_bad_8x8_pattern(self):self.bad(lambda j:j['tiles']['sky'].__setitem__(0,'zzzzzzzz'))
    def test_out_of_bounds_entity(self):self.bad(lambda j:j['entities'][0].__setitem__('x',64))
    def test_flag_not_after_spawn(self):self.bad(lambda j:j['entities'][0].__setitem__('x',62))
    def test_boolean_x_rejected(self):self.bad(lambda j:j['entities'][0].__setitem__('x',True))
    def test_invalid_palette(self):self.bad(lambda j:j['palette'].__setitem__(0,999))
    def test_bat_stride_rejected(self):self.bad(lambda j:j.__setitem__('map',[x[:31] for x in j['map']]))
    def test_pattern_overlaps_bat(self):self.bad(lambda j:j.__setitem__('pattern_word',0x700))
    def test_generated_compiles_as_c(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=packer.produce(packer.compiled(packer.load(SAMPLE)),tmp)
            self.assertEqual(result['bat_bytes'],3584)
            h=(Path(tmp)/'level_art.h').read_text()
            c=(Path(tmp)/'level_art.c').read_text()
            self.assertIn('LEVEL_SOLID_STRIDE',h)
            self.assertIn('level_patterns[]',c)
            self.assertNotIn(',,',c)
            self.assertIn('const uint16_t level_palette[16]',c)

if __name__=='__main__':unittest.main()

class RecipeRoutingTests(unittest.TestCase):
    def test_cd_request_warns_when_gameplay_starter_is_hucard(self):
        offline=load('offline')
        result=offline.guidance(offline.choose('one minute platformer for Super CD-ROM2'), 'one minute platformer for Super CD-ROM2')
        self.assertEqual(result['recipe'],'platformer')
        self.assertEqual(result['requested_target'],'supercd')
        self.assertFalse(result['target_matches_request'])
        self.assertTrue(any('cold-boot' in x for x in result['instructions']))
    def test_level_recipe_scaffolds_standalone(self):
        offline=load('offline')
        self.assertEqual(offline.choose('generated tilemap tileset'),'level')
        import subprocess,sys
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'level'
            run=subprocess.run([sys.executable,str(ROOT/'offline.py'),'new','--recipe','level','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertTrue((out/'assets/level.json').is_file())
            self.assertTrue((out/'tools/assetpack.py').is_file())
            self.assertFalse((out/'build').exists())

class ActualSdkSymbolTests(unittest.TestCase):
    def test_sdk_declaration_in_fixture_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'hardware.h').write_text('#define KEY_RUN 0x08\n#define VDC_SPRITE_FLIP_X 0x800\n')
            hits=guard.installed_sdk_declarations('KEY_RUN',tmp)
            self.assertEqual(len(hits),1)
            self.assertEqual(hits[0]['line'],1)
    def test_bad_identifier_rejected(self):
        with self.assertRaises(ValueError):guard.installed_sdk_declarations('KEY_RUN; rm -rf /')
