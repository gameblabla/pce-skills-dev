#!/usr/bin/env python3
"""Bake a fixed-grid PNG sprite sheet into shared-palette PCE sprite patterns."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from formats import indexed, pack_sprite, palette_for, vce_rgb


def parse_size(text):
    try:
        width, height = (int(part, 10) for part in text.lower().split('x', 1))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError('size must be WIDTHxHEIGHT, such as 64x64')
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError('frame dimensions must be positive')
    return width, height


def parse_point(text):
    try:
        x, y = (int(part, 10) for part in text.split(',', 1))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError('anchor must be X,Y')
    return x, y


def convert(source, prefix, frame_size=None, anchor=(0, 0)):
    source = Path(source)
    prefix = Path(prefix)
    sheet = Image.open(source).convert('RGBA')
    frame_width, frame_height = frame_size or sheet.size
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError('frame dimensions must be positive')
    if sheet.width % frame_width or sheet.height % frame_height:
        raise ValueError('sheet dimensions must be exact multiples of the frame dimensions')

    frames = []
    locations = []
    for y in range(0, sheet.height, frame_height):
        for x in range(0, sheet.width, frame_width):
            frames.append(sheet.crop((x, y, x + frame_width, y + frame_height)))
            locations.append((x, y))
    palette = palette_for(frames)

    pattern_bytes = bytearray()
    piece_bytes = bytearray()
    preview = Image.new('RGBA', sheet.size, (0, 0, 0, 0))
    frame_records = []
    palette_rgb = vce_rgb(palette).astype(np.uint8)
    for frame_index, (frame, location) in enumerate(zip(frames, locations)):
        patterns, pieces, _, max_line_entries = pack_sprite(frame, anchor, palette)
        if len(pieces) > 64:
            raise ValueError(f'frame {frame_index} exceeds the 64-entry SAT limit')
        first_pattern = len(pattern_bytes) // 128
        first_piece = len(piece_bytes) // 6
        for x, y, local_pattern in pieces:
            global_pattern = first_pattern + local_pattern
            if global_pattern > 0xffff:
                raise ValueError('sheet contains more than 65536 sprite patterns')
            piece_bytes.extend(struct.pack('<hhH', x, y, global_pattern))
        pattern_bytes.extend(patterns)

        index = indexed(frame, palette)
        rgba = np.empty((frame_height, frame_width, 4), np.uint8)
        rgba[..., :3] = palette_rgb[index]
        rgba[..., 3] = np.where(index == 0, 0, 255)
        preview.alpha_composite(Image.fromarray(rgba), location)

        line_entries = [0] * frame_height
        for _, y, _ in pieces:
            source_y = y + anchor[1]
            for line in range(max(0, source_y), min(frame_height, source_y + 16)):
                line_entries[line] += 1
        frame_records.append({
            'frame': frame_index,
            'sheet_origin': list(location),
            'pixels': [frame_width, frame_height],
            'anchor': list(anchor),
            'first_pattern': first_pattern,
            'pattern_count': len(patterns) // 128,
            'first_piece': first_piece,
            'piece_count': len(pieces),
            'max_16px_entries_on_scanline': max_line_entries,
            'line_entries': line_entries,
        })

    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        'patterns': prefix.with_name(prefix.name + '.patterns.bin'),
        'pieces': prefix.with_name(prefix.name + '.pieces.bin'),
        'palette': prefix.with_name(prefix.name + '.palette.bin'),
        'preview': prefix.with_name(prefix.name + '.preview.png'),
        'manifest': prefix.with_name(prefix.name + '.json'),
    }
    paths['patterns'].write_bytes(pattern_bytes)
    paths['pieces'].write_bytes(piece_bytes)
    paths['palette'].write_bytes(palette.astype('<u2', copy=False).tobytes())
    preview.save(paths['preview'])
    manifest = {
        'format': 'pce-sprite-sheet-v1',
        'source': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sheet_pixels': list(sheet.size),
        'frame_grid': [sheet.width // frame_width, sheet.height // frame_height],
        'frame_pixels': [frame_width, frame_height],
        'palette_entries': 16,
        'transparent_index': 0,
        'pattern_bytes_per_16x16_piece': 128,
        'piece_record': 'little-endian int16 x, int16 y, uint16 global pattern index',
        'pattern_count': len(pattern_bytes) // 128,
        'piece_count': len(piece_bytes) // 6,
        'files': {name: {'name': path.name, 'bytes': path.stat().st_size}
                  for name, path in paths.items() if name != 'manifest'},
        'frames': frame_records,
        'notes': [
            'All frames share one palette so animation cannot change colors between frames.',
            'Each emitted SAT piece is one 16x16 pattern. The runtime must still admit objects against the global SAT and scanline budgets.',
            'Use the preview to inspect the actual 9-bit VCE palette quantization and transparency.',
        ],
    }
    paths['manifest'].write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='PNG containing one sprite or a fixed-cell sprite sheet')
    parser.add_argument('--out', type=Path, required=True, help='output prefix')
    parser.add_argument('--frame', type=parse_size,
                        help='grid cell size; defaults to treating the whole image as one sprite')
    parser.add_argument('--anchor', type=parse_point, default=(0, 0),
                        help='shared sprite origin within each cell, such as 32,32')
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.out, args.frame, args.anchor), indent=2))


if __name__ == '__main__':
    main()
