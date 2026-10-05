#!/usr/bin/env python3
"""Rank linker-reported bank headroom; this does not prove a bank is safe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def parse_bank(value: object) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.startswith("$"):
        return int(text[1:], 16)
    return int(text, 0)


def parse_excludes(value: str | None) -> set[int]:
    if not value:
        return set()
    return {parse_bank(part) for part in value.split(",") if part.strip()}


def bank_rows(data: dict, bank_size: int | None) -> list[dict]:
    entries = data.get("banks")
    if isinstance(entries, list) and entries:
        rows = []
        for entry in entries:
            bank = parse_bank(entry["bank"])
            free = entry.get("free", entry.get("free_bytes", entry.get("available")))
            used = entry.get("used", entry.get("used_bytes"))
            capacity = entry.get("capacity", entry.get("size"))
            if free is None:
                if capacity is None and bank_size is not None:
                    capacity = bank_size
                if capacity is None or used is None:
                    continue
                free = int(capacity) - int(used)
            rows.append({"bank": bank, "used": used, "free": int(free), "capacity": capacity})
        if rows:
            return rows

    if bank_size is None:
        raise ValueError("report has no usable 'banks' rows; provide --bank-size for section-only reports")
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise ValueError("report must contain a 'banks' or 'sections' list")
    totals: dict[int, int] = {}
    for section in sections:
        if "bank" not in section:
            continue
        bank = parse_bank(section["bank"])
        size = section.get("bytes", section.get("size"))
        if size is None:
            continue
        totals[bank] = totals.get(bank, 0) + int(size)
    return [
        {"bank": bank, "used": used, "free": bank_size - used, "capacity": bank_size}
        for bank, used in totals.items()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="linker/runtime JSON report")
    parser.add_argument("--needed", type=int, default=0, help="minimum required free bytes")
    parser.add_argument("--exclude", help="comma-separated bank numbers, e.g. 0x76,0x77 or $76,$77")
    parser.add_argument("--bank-size", type=int, help="capacity per bank, required for section-only reports")
    parser.add_argument("--limit", type=int, default=0, help="maximum number of rows to print; 0 means all")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    try:
        data = json.loads(args.report.read_text(encoding="utf-8"))
        excluded = parse_excludes(args.exclude)
        rows = [row for row in bank_rows(data, args.bank_size) if row["bank"] not in excluded]
        rows.sort(key=lambda row: (-row["free"], row["bank"]))
        if args.limit:
            rows = rows[: args.limit]
        if args.json:
            for row in rows:
                row["meets_needed"] = row["free"] >= args.needed
            print(json.dumps({"capacity_only": True, "needed": args.needed, "banks": rows}, indent=2))
        else:
            print("bank\tused\tfree\tmeets_needed")
            for row in rows:
                used = "unknown" if row["used"] is None else str(row["used"])
                print(f"0x{row['bank']:02X}\t{used}\t{row['free']}\t{row['free'] >= args.needed}")
            print("Capacity ranking only. Verify mappings, overlays, reservations, callers, and data lifetime before moving code.")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
