#!/usr/bin/env python3
"""End-to-end check of the vendored Mednafen native profiler RPC.

Requires a built pce-headless and a bootable PCE ROM; never downloads assets.
"""
import argparse
from pathlib import Path
import tempfile

from cycle_profile import RPC, read_profile, validate_native_dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True)
    args = parser.parse_args()
    if not args.emulator.is_file() or not args.rom.is_file():
        parser.error('emulator and ROM must exist; run make headless-build first')
    with tempfile.TemporaryDirectory(prefix='pce-profiler-smoke-') as temporary:
        root = Path(temporary)
        rpc = RPC(args.emulator.resolve(), args.rom.resolve(), root/'emulator')
        try:
            try:
                rpc.call('prof_dump', root/'unstarted.cycles')
            except ValueError as exc:
                if 'active prof_start' not in str(exc):
                    raise
            else:
                raise ValueError('prof_dump unexpectedly succeeded without prof_start')
            totals = []
            for i in range(2):
                rpc.call('prof_start')
                rpc.call('run', 10)
                output = root/f'segment-{i}.cycles'
                native = rpc.call('prof_dump', output)
                records = read_profile(output)
                validate_native_dump(native, records)
                ticks = sum(records.values())
                if not 2500000 <= ticks <= 5000000:
                    raise ValueError(f'implausible 10-frame profiler total: {ticks}')
                totals.append(ticks)
            # A stationary empty-loop ROM should consume a nearly identical
            # 10-frame master-clock budget in independent profiling windows.
            if abs(totals[1]-totals[0]) > 20000:
                raise ValueError(f'profiling windows differ unexpectedly: {totals}')
            rpc.call('prof_start')
            rpc.call('run', 2)
            try:
                rpc.call('prof_dump', root/'missing-parent'/'cannot-write.cycles')
            except ValueError as exc:
                if 'cannot open profile output' not in str(exc):
                    raise
            else:
                raise ValueError('prof_dump unexpectedly succeeded with unwritable path')
            print(f'PASS: two independent windows ({totals[0]}, {totals[1]} master ticks), '
                  'native metadata matches histogram; invalid dump rejected')
        finally:
            rpc.close()


if __name__ == '__main__':
    main()
