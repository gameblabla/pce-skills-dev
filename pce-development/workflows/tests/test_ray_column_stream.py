"""Offline invariants for the fast, VRAM-resident full-detail raycaster."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
TOOLS=ROOT/'tools'
sys.path.insert(0,str(TOOLS))
import gen_backdrop
import gen_sparse_irq
import column_benchmark
import bitmap_stress

class ColumnStreamTests(unittest.TestCase):
    def test_background_is_precomputed_and_deterministic(self):
        self.assertEqual((ROOT/'src/backdrop_words.h').read_text(),gen_backdrop.generate())
        # The bitmap now uses a deterministic procedural 128x128 backdrop
        # instead of the old 14-row checkerboard.  Its 8,192 words remain
        # entirely VDC-resident; no framebuffer or extra per-frame upload.
        rows=[[gen_backdrop.backdrop(y,p) for p in range(64)] for y in range(128)]
        self.assertEqual(len(rows)*len(rows[0]),8192)
        self.assertTrue(all(0xf200<=v<=0xf2ff for row in rows for v in row))
        self.assertGreater(len(set(tuple(row) for row in rows[:64])),8)
        self.assertGreater(len(set(tuple(row) for row in rows[64:])),20)
        self.assertGreater(len(set(v for row in rows for v in row)),14)

    def test_compact_backdrop_lut_preserves_every_pixel_pair(self):
        # Repeating periods follow paired-pixel sky dithering and floor U
        # addressing, not approximate palette quantization. Expand the table
        # over the complete 128x64 BAT and compare with the source algorithm.
        shifts=[0 if y<66 else 4 if y<73 else 3 if y<82 else 2 if y<101 else 1
                for y in range(128)]
        periods=[2 if y<64 else 32 >> shifts[y] for y in range(128)]
        self.assertEqual(sum(periods),826)
        offsets=[]
        table=[]
        for y,period in enumerate(periods):
            offsets.append(len(table))
            table.extend(gen_backdrop.backdrop(y,p) for p in range(period))
        self.assertEqual(offsets[-1]+periods[-1],len(table))
        for y in range(128):
            for p in range(64):
                self.assertEqual(table[offsets[y]+(p & (periods[y]-1))],
                                 gen_backdrop.backdrop(y,p), (y,p))
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('RAY_BACKDROP_FAST_WORD(y,pair)',src)
        self.assertIn('RAY_BACKDROP_FAST_WORD(y,p)',src)

    def test_multiple_pairs_fit_the_same_upload_budget(self):
        src=(ROOT/'src/main.c').read_text()
        block=src.split('static void stage_columns(void) {',1)[1].split('static void render_columns(void) {',1)[0]
        self.assertIn('budget=(uint8_t)(budget-count)',block)
        self.assertIn('staged_segment_count[segments]=count',block)
        self.assertIn('staged_segment_count[segments]=0u',block)
        self.assertIn('if(count!=remaining)break;',block)
        self.assertNotIn('finish_column(pair)',block)
        # Clean and dirty metadata may only advance the official cursor
        # after the corresponding real writes complete under the IRQ mask.
        write=src.rsplit('static void render_columns(void) {',1)[1].split('#endif\n#endif',1)[0]
        self.assertLess(write.index('pce_memop('),write.index('finish_column(pair)'))
        self.assertIn('if(n>until_page)n=until_page;',write)

    def test_sparse_irq_is_host_generated_and_schedules_127_changes(self):
        self.assertEqual((ROOT/'src/bat_sparse_irq.S').read_text(),gen_sparse_irq.gen())
        lines=[(y*7+3)//4 for y in range(1,128)]
        self.assertEqual(len(lines),127)
        self.assertEqual(lines[:4],[2,4,6,7])
        self.assertEqual(lines[-1],223)
        self.assertEqual(len(lines),len(set(lines)))
        self.assertEqual(sum(1 for y in range(128) if y==64),1)
        self.assertNotIn('st2 #2\n.Lno_page:',gen_sparse_irq.gen().split('cpy #64')[0])

    def test_second_page_scroll_guard_matches_staged_upload_wrap(self):
        # Logical y=64 must resolve to the *same physical BAT row* that
        # was active immediately before the mid-screen BXR page flip.
        # A stale BYR then draws wall pixels instead of a floor-colored line.
        self.assertEqual(gen_sparse_irq.bat_row(63),63)
        self.assertEqual(gen_sparse_irq.bat_row(64),63)
        self.assertEqual(gen_sparse_irq.bat_row(65),0)
        self.assertEqual(gen_sparse_irq.bat_row(127),62)
        self.assertEqual(set(gen_sparse_irq.bat_row(y) for y in range(64,128)),set(range(64)))
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('((y-1u)&63u)',src)
        self.assertIn('if(n>until_page)n=until_page;',src)
        self.assertIn('y==64u?65u:128u',src)

    def test_midpoint_stripe_detector_uses_physical_pixels(self):
        from PIL import Image,ImageDraw
        from raster_sweep import midpoint_seam_metrics
        image=Image.new('RGB',(560,242),(72,72,72))
        draw=ImageDraw.Draw(image)
        for x in range(24,536,8):
            color=(108,72,36) if (x//8)&1 else (72,72,36)
            draw.rectangle((x,234,x+7,234),fill=color)
            draw.rectangle((x,124,x+7,124),fill=color)
        self.assertTrue(midpoint_seam_metrics(image)['defective'])
        draw.rectangle((24,124,535,124),fill=(72,72,72))
        self.assertFalse(midpoint_seam_metrics(image)['defective'])

    def test_vertical_vram_increment_and_short_irq_masks(self):
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('VDC_CONTROL_VRAM_ADD_128',src)
        self.assertIn('RAY_COLUMN_CHUNK_WORDS 8u',src)
        self.assertIn('column_pass_dirty',src)
        self.assertIn('ray_bat_words',src)
        self.assertIn('if(cast_valid && cast_angle==angle',src)
        self.assertIn('if(i && next_column==0u)break;',src)
        self.assertIn('column_prepare()',src)
        self.assertIn('upload_next_y=(uint8_t)(upload_next_y+n)',src)
        self.assertIn('if(upload_active)return 1u;',src)
        self.assertIn('pce_cpu_irq_enable();',src)
        make=(ROOT/'Makefile').read_text()
        self.assertIn('src/bat_sparse_irq.S',make)
        self.assertIn('src/bat_bitmap_irq.S',make) # atomic/reference remain independent
        self.assertIn('__rom_bank0_size=0x8000',make)
        self.assertIn('$(MAKE) raster-sweep',make)

    def test_quality_shader_runs_before_the_vblank_transfer(self):
        src=(ROOT/'src/main.c').read_text()
        mk=(ROOT/'Makefile').read_text()
        self.assertIn('-DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0',mk)
        self.assertIn('#define RAY_VBLANK_WORD_BUDGET 96u',src)
        self.assertIn('static void stage_pair_words(uint8_t pair,uint8_t first,uint8_t count,uint16_t *dest)',src)
        self.assertIn('ray_wall_hires[sl>>1][ray_tex_phase[l]>>3]',src)
        self.assertIn('if(count)stage_pair_words(pair,local_next,count,staged_words+total);',src)
        self.assertIn('if(pending)stage_columns();',src)
        self.assertIn('if(pending) render_columns();',src)
        self.assertLess(src.index('if(pending)stage_columns();'),
                        src.index('uint8_t before=bat_frames;while(before==bat_frames){}'))
        # No data-port operations are allowed inside the unmasked shader;
        # its output is buffered for the short vertical-blank transfers.
        shader=src.split('static void stage_pair_words(',1)[1].split('static void stage_columns(',1)[0]
        self.assertNotIn('IO_VDC_DATA',shader)
        self.assertNotIn('pce_cpu_irq_disable',shader)
        # Resolve the vertical and horizontal texture strips once per pair;
        # a separate ROM-address calculation for every pixel costs HuC6280 cycles.
        setup,loop=shader.split('for(uint8_t j=0;j<count;++j)',1)
        self.assertIn('const uint8_t *wl=',setup)
        self.assertIn('const uint8_t *wr=',setup)
        self.assertIn('const uint8_t *vl=',setup)
        self.assertIn('const uint8_t *vr=',setup)
        self.assertNotIn('ray_wall_hires[',loop)
        self.assertNotIn('ray_sheet_pairs[',loop)
        render=src.split('static void render_columns(void) {',2)[-1].split('#endif\n#endif',1)[0]
        self.assertIn('if(n>8u)n=8u;',render)
        self.assertIn('pce_cpu_irq_enable();',render)

    def test_interaction_trace_waits_for_one_time_bitmap_initialization(self):
        import json
        scenario=json.loads((ROOT/'tools/interaction-scenario.json').read_text())
        self.assertEqual(scenario['boot_frames'],180)
        runner=(ROOT/'tools/genre_trace.py').read_text()
        self.assertIn("boot_frames=scenario.get('boot_frames',initial_frames)",runner)
        self.assertIn('client=old.NativeControl(str(exe),rom,base_dir,bios,boot_frames)',runner)

    def sample(self):
        result=[]
        for name,frames,buttons in column_benchmark.SCENARIO:
            result.append({'segment':name,'emulator_frames':frames,
                           'buttons':list(buttons),'dirty_views':0,'vram_words':0,
                           'game_updates':frames//2,'screenshot_colors':12})
        for n in ('turn-right','walk','turn-left'):
            x=next(s for s in result if s['segment']==n)
            x['dirty_views']=5;x['vram_words']=4000
        return result

    def test_real_dirty_view_accounting(self):
        report=column_benchmark.validate(self.sample())
        self.assertTrue(report['passed'])
        self.assertEqual(report['changed_views'],15)
        self.assertEqual(report['turning_views_per_second'],
                         round(10*60/(column_benchmark.SCENARIO[1][1]+column_benchmark.SCENARIO[3][1]),3))

    def test_column_bitmap_stress_allows_incomplete_settle_pass(self):
        # With bounded/resumable VRAM writes, some controller segments end
        # in the middle of a changed view; screenshots must still be valid.
        redraws=(1,2,3,4,4,5)
        samples=[{'segment':i,'emulator_frames':bitmap_stress.STEPS[i][0],
                  'total_redraws':r,'game_updates':(i+1)*100,
                  'bitmap':{'passed':True}} for i,r in enumerate(redraws)]
        self.assertEqual(bitmap_stress.validate(samples,column_mode=True)['completed_redraws'],5)
        samples[-1]['total_redraws']=10000
        with self.assertRaisesRegex(ValueError,'impossible redraw'):
            bitmap_stress.validate(samples,column_mode=True)

    def test_rejects_fake_frame_without_actual_vram_writes(self):
        rows=self.sample();rows[1]['vram_words']=0
        with self.assertRaisesRegex(ValueError,'fabricated'):column_benchmark.validate(rows)

    def test_rejects_idle_only_fake_speed(self):
        rows=self.sample();rows[-1]['dirty_views']=2;rows[-1]['vram_words']=500
        with self.assertRaisesRegex(ValueError,'fully settled idle'):column_benchmark.validate(rows)

    def test_rejects_blank_screenshot_or_stalled_game(self):
        rows=self.sample();rows[1]['screenshot_colors']=1
        with self.assertRaisesRegex(ValueError,'unrendered'):column_benchmark.validate(rows)
        rows=self.sample();rows[1]['game_updates']=0
        with self.assertRaisesRegex(ValueError,'stalled'):column_benchmark.validate(rows)

    def test_rejects_missing_turns(self):
        rows=self.sample();rows[1]['dirty_views']=0;rows[3]['dirty_views']=0
        with self.assertRaisesRegex(ValueError,'rotation failed'):column_benchmark.validate(rows)

if __name__=='__main__':unittest.main()
