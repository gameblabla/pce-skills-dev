#!/usr/bin/env python3
"""Compare the same two-colour VBlank-flipping renderer with/without ROM tables.

Complete page flips are not progressive dirty-view commits. This comparison
checks exact stationary RGB equality and reports completed VBlank flips, NOT
nominal video frames or DMA-copy completion counts.
"""
import argparse
import json
from pathlib import Path

from column_benchmark import run as benchmark
from wall_equivalence import run as visual


def run(reference, optimized, output):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline = benchmark(reference, str(reference) + '.elf',
                         output.with_name(output.stem + '-reference.json'))
    candidate = benchmark(optimized, str(optimized) + '.elf',
                          output.with_name(output.stem + '-optimized.json'))
    v = visual(reference, optimized, output.with_name(output.stem + '-pixels.json'))
    if not v['matched'] or v['differing_pixels']:
        raise ValueError('tiled VBlank pageflip must be pixel-identical to its legacy converter')
    if candidate['totals']['turning_views_per_second'] < baseline['totals']['turning_views_per_second']:
        raise ValueError('lookup quantizer decreased completed turning page flips')
    result = {
        'passed': True,
        'presentation': 'complete VBlank BAT selection between two lossily quantized 128x128 tiled pages',
        'baseline_flips_per_second_turning': baseline['totals']['turning_views_per_second'],
        'optimized_flips_per_second_turning': candidate['totals']['turning_views_per_second'],
        'baseline_flips_total': baseline['totals']['changed_views'],
        'optimized_flips_total': candidate['totals']['changed_views'],
        'baseline_bat_words': baseline['totals']['vram_words'],
        'optimized_bat_words': candidate['totals']['vram_words'],
        'stationary_differing_pixels': v['differing_pixels'],
        'stationary_pixels_compared': v['pixel_count'],
        'limitations': [
            'The 2-colour tile format is posterized and NOT equivalent to the 16-colour paired-BAT renderer',
            'Video timing and VBlank flipping are emulator-only, not physical console validation',
            'Benchmarked camera paths can differ because game-loop throughput differs',
        ],
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True)
    p.add_argument('--optimized', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    try:
        run(args.reference, args.optimized, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        p.error(str(error))
