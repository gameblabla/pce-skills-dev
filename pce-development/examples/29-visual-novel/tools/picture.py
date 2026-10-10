#!/usr/bin/env python3
"""Bake a PNG into PCE background patterns, VCE palettes, and a BAT image."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from formats import planar_tile, vce_rgb
import palfit


def parse_size(text):
    try:
        width, height = (int(part, 10) for part in text.lower().split('x', 1))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError('size must be WIDTHxHEIGHT, such as 320x224')
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError('dimensions must be positive')
    return width, height


def convert(source, prefix, canvas_size=(320, 224), pattern_word=0x0800, bat_width=64):
    source = Path(source)
    prefix = Path(prefix)
    width, height = canvas_size
    if width % 8 or height % 8:
        raise ValueError('canvas dimensions must be multiples of 8 pixels')
    if bat_width not in (32, 64, 128) or width // 8 > bat_width:
        raise ValueError('BAT width must be 32, 64, or 128 characters and fit the canvas')
    if height // 8 > 64:
        raise ValueError('canvas is taller than a 64-row BAT')
    if pattern_word < 0 or pattern_word >= 0x8000 or pattern_word % 16:
        raise ValueError('pattern-word must be a 16-word-aligned VDC word address')

    artwork = Image.open(source).convert('RGBA')
    if artwork.width > width or artwork.height > height:
        raise ValueError(f'image {artwork.width}x{artwork.height} exceeds canvas {width}x{height}')
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(artwork, (0, 0))
    rgba = np.asarray(canvas)
    tile_width, tile_height = width // 8, height // 8
    cells = (rgba.reshape(tile_height, 8, tile_width, 8, 4)
             .transpose(0, 2, 1, 3, 4).reshape(-1, 8, 8, 4))

    palettes, groups = palfit.fit_palettes(cells, 16, verbose=False)
    indices = palfit.index_cells(cells, palettes, groups)

    blank = planar_tile(np.zeros((8, 8), np.uint8))
    patterns = [blank]
    pattern_ids = {blank: 0}
    cell_ids = np.empty(len(cells), np.uint16)
    for cell_number, index in enumerate(indices):
        pattern = planar_tile(index)
        tile_id = pattern_ids.get(pattern)
        if tile_id is None:
            tile_id = len(patterns)
            pattern_ids[pattern] = tile_id
            patterns.append(pattern)
        cell_ids[cell_number] = tile_id

    tile_base = pattern_word // 16
    if tile_base + len(patterns) > 2048 or pattern_word + len(patterns) * 16 > 0x8000:
        raise ValueError('patterns exceed the BAT tile-number field or VDC VRAM')

    bat = bytearray()
    for y in range(tile_height):
        for x in range(bat_width):
            if x < tile_width:
                cell_number = y * tile_width + x
                tile_id = int(cell_ids[cell_number])
                palette_id = int(groups[cell_number])
            else:
                tile_id = 0
                palette_id = 0
            entry = (tile_base + tile_id) | (palette_id << 12)
            bat.extend(entry.to_bytes(2, 'little'))

    palette_bytes = palettes.astype('<u2', copy=False).tobytes()
    pattern_bytes = b''.join(patterns)
    decoded = np.empty((height, width, 4), np.uint8)
    for cell_number, index in enumerate(indices):
        y, x = divmod(cell_number, tile_width)
        palette = vce_rgb(palettes[int(groups[cell_number])]).astype(np.uint8)
        tile_rgba = np.empty((8, 8, 4), np.uint8)
        tile_rgba[..., :3] = palette[index]
        tile_rgba[..., 3] = 255
        decoded[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = tile_rgba

    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        'patterns': prefix.with_name(prefix.name + '.patterns.bin'),
        'palettes': prefix.with_name(prefix.name + '.palettes.bin'),
        'bat': prefix.with_name(prefix.name + '.bat.bin'),
        'preview': prefix.with_name(prefix.name + '.preview.png'),
        'manifest': prefix.with_name(prefix.name + '.json'),
    }
    paths['patterns'].write_bytes(pattern_bytes)
    paths['palettes'].write_bytes(palette_bytes)
    paths['bat'].write_bytes(bat)
    Image.fromarray(decoded).save(paths['preview'])
    manifest = {
        'format': 'pce-static-background-v1',
        'source': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'canvas_pixels': [width, height],
        'visible_characters': [tile_width, tile_height],
        'bat_width_characters': bat_width,
        'pattern_word_address': pattern_word,
        'pattern_character_base': tile_base,
        'pattern_count_including_blank': len(patterns),
        'palette_count': 16,
        'palette_words_per_palette': 16,
        'files': {name: {'name': path.name, 'bytes': path.stat().st_size}
                  for name, path in paths.items() if name != 'manifest'},
        'notes': [
            'Pattern and BAT addresses use VDC word and character units respectively.',
            'Palette entry zero is the shared backdrop color; transparency is retained as pixel index zero.',
            'This is a baked asset set, not a project-specific CD loader or display routine.',
        ],
    }
    paths['manifest'].write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='source PNG')
    parser.add_argument('--out', type=Path, required=True, help='output prefix')
    parser.add_argument('--canvas', type=parse_size, default=(320, 224),
                        help='output size, WIDTHxHEIGHT; defaults to Saber Rider UI size')
    parser.add_argument('--pattern-word', type=lambda value: int(value, 0), default=0x0800,
                        help='VDC word address for the first pattern; default matches Saber Rider UI')
    parser.add_argument('--bat-width', type=int, default=64,
                        help='VDC BAT row width in characters: 32, 64, or 128')
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.out, args.canvas,
                             args.pattern_word, args.bat_width), indent=2))


if __name__ == '__main__':
    main()
