#!/usr/bin/env python3
"""Convert a bright-on-dark 8x8 glyph sheet into PCE background font tiles."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from formats import planar_tile, vce_rgb


def convert(source, prefix, first_code=32, count=None, pattern_word=0x4200,
            palette_id=15, ink=0x01ff, threshold=128, pen=15):
    source = Path(source)
    prefix = Path(prefix)
    rgba = np.asarray(Image.open(source).convert('RGBA'))
    if rgba.shape[1] % 8 or rgba.shape[0] % 8:
        raise ValueError('glyph sheet width and height must be multiples of 8')
    if pattern_word < 0 or pattern_word >= 0x8000 or pattern_word % 16:
        raise ValueError('pattern-word must be a 16-word-aligned VDC word address')
    if not 1 <= pen <= 15:
        raise ValueError('font pen must be from 1 through 15')
    if not 0 <= threshold <= 255:
        raise ValueError('threshold must be from 0 through 255')
    if not 0 <= palette_id < 16 or not 0 <= ink < 512:
        raise ValueError('palette id must be 0..15 and ink must be a 9-bit VCE color')

    width, height = rgba.shape[1] // 8, rgba.shape[0] // 8
    available = width * height
    count = available if count is None else count
    if count <= 0 or count > available:
        raise ValueError(f'count must be between 1 and {available}')
    if first_code < 0 or first_code + count > 256:
        raise ValueError('this bitmap tool emits byte character codes (0..255)')
    tile_base = pattern_word // 16
    if tile_base + count > 2048 or pattern_word + count * 16 > 0x8000:
        raise ValueError('font patterns exceed the BAT tile-number field or VDC VRAM')

    patterns = bytearray()
    masks = []
    for glyph in range(count):
        x, y = (glyph % width) * 8, (glyph // width) * 8
        cell = rgba[y:y + 8, x:x + 8]
        luminance = (cell[..., 0].astype(np.uint16) * 299 +
                     cell[..., 1].astype(np.uint16) * 587 +
                     cell[..., 2].astype(np.uint16) * 114) // 1000
        mask = (cell[..., 3] >= 128) & (luminance >= threshold)
        masks.append(mask)
        patterns.extend(planar_tile(mask.astype(np.uint8) * pen))

    palettes = np.zeros((16, 16), dtype='<u2')
    palettes[palette_id, pen] = ink
    palette_words = palettes.astype('<u2', copy=False)
    ink_rgb = vce_rgb(np.asarray([ink], dtype=np.uint16))[0].astype(np.uint8)
    preview = np.zeros((height * 8, width * 8, 4), np.uint8)
    for glyph, mask in enumerate(masks):
        x, y = (glyph % width) * 8, (glyph // width) * 8
        target = preview[y:y + 8, x:x + 8]
        target[..., :3] = ink_rgb
        target[..., 3] = mask.astype(np.uint8) * 255

    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        'patterns': prefix.with_name(prefix.name + '.patterns.bin'),
        'palettes': prefix.with_name(prefix.name + '.palettes.bin'),
        'preview': prefix.with_name(prefix.name + '.preview.png'),
        'header': prefix.with_name(prefix.name + '.h'),
        'manifest': prefix.with_name(prefix.name + '.json'),
    }
    paths['patterns'].write_bytes(patterns)
    paths['palettes'].write_bytes(palette_words.tobytes())
    Image.fromarray(preview).save(paths['preview'])
    paths['header'].write_text(
        '#pragma once\n'
        f'#define PCE_FONT_FIRST_CODE {first_code}\n'
        f'#define PCE_FONT_GLYPH_COUNT {count}\n'
        f'#define PCE_FONT_PATTERN_WORD 0x{pattern_word:04x}\n'
        f'#define PCE_FONT_TILE_BASE {tile_base}\n'
        f'#define PCE_FONT_PALETTE {palette_id}\n'
        f'#define PCE_FONT_PEN {pen}\n')
    manifest = {
        'format': 'pce-bitmap-font-v1',
        'source': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sheet_grid': [width, height],
        'glyph_pixels': [8, 8],
        'first_code': first_code,
        'glyph_count': count,
        'pattern_word_address': pattern_word,
        'pattern_character_base': tile_base,
        'palette_id': palette_id,
        'pixel_pen': pen,
        'ink_vce_color': ink,
        'files': {name: {'name': path.name, 'bytes': path.stat().st_size}
                  for name, path in paths.items() if name != 'manifest'},
        'notes': [
            'Each glyph cell is row-major and becomes one 8x8 background pattern.',
            'The sheet is thresholded as bright foreground on dark or transparent background.',
            'Upload the emitted palette and patterns before writing BAT entries for text.',
        ],
    }
    paths['manifest'].write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='PNG glyph sheet; row-major 8x8 cells')
    parser.add_argument('--out', type=Path, required=True, help='output prefix')
    parser.add_argument('--first-code', type=int, default=32)
    parser.add_argument('--count', type=int, help='glyph count; default is all complete cells')
    parser.add_argument('--pattern-word', type=lambda value: int(value, 0), default=0x4200,
                        help='VDC word address; default matches Saber Rider font placement')
    parser.add_argument('--palette', type=int, default=15)
    parser.add_argument('--ink', type=lambda value: int(value, 0), default=0x01ff,
                        help='9-bit VCE color code')
    parser.add_argument('--threshold', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.out, args.first_code, args.count,
                             args.pattern_word, args.palette, args.ink, args.threshold),
                     indent=2))


if __name__ == '__main__':
    main()
