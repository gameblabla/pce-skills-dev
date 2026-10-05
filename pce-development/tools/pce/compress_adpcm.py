#!/usr/bin/env python3
"""Encode audio for the PCE CD ADPCM path and write a decoded WAV preview."""
import argparse
import array
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

from adpcm import decode, encode


def convert(source, destination, rate):
    if rate <= 0:
        raise ValueError('sample rate must be positive')
    result = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(source), '-ac', '1', '-ar', str(rate),
         '-f', 's16le', '-'],
        check=True, capture_output=True)
    if len(result.stdout) & 1:
        raise ValueError('ffmpeg returned a partial PCM sample')

    pcm = array.array('h')
    pcm.frombytes(result.stdout)
    if sys.byteorder != 'little':
        pcm.byteswap()

    packed = encode(pcm)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(packed)

    # The encoder pads an odd trailing nibble; keep the preview at source length.
    preview = array.array('h', decode(packed)[:len(pcm)])
    if sys.byteorder != 'little':
        preview.byteswap()
    preview_path = destination.with_suffix('.decoded.wav')
    with wave.open(str(preview_path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(preview.tobytes())

    report = {
        'format': 'pce-cd-adpcm-msm5205-compatible-nibbles',
        'nibble_order': 'high-nibble-first',
        'samples': len(pcm),
        'encoded_bytes': len(packed),
        'sample_rate': rate,
        'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        'encoded_sha256': hashlib.sha256(packed).hexdigest(),
        'decoded_preview': preview_path.name,
    }
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='audio file readable by ffmpeg')
    parser.add_argument('output', type=Path, help='raw encoded ADPCM output')
    parser.add_argument('--rate', type=int, required=True,
                        help='target PCM rate used to create the source stream')
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.output, args.rate), indent=2))


if __name__ == '__main__':
    main()
