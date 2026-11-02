#!/usr/bin/env python3
"""Write screenshot candidates to a CSV. Does not delete any photo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.cli import DATA_OUT, DATA_RAW, emit_notes, fail, open_photos_source, project_path
from iphone_cleanup.photos import list_export_rows, list_screenshot_rows, write_screenshot_csv
from iphone_cleanup.timestamps import format_bytes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List screenshot candidates. Nothing is deleted.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--backup", type=project_path)
    source.add_argument("--photos-sqlite", type=project_path)
    source.add_argument("--export-dir", type=project_path)
    parser.add_argument("--out", type=project_path, default=DATA_OUT / "screenshots.csv")
    parser.add_argument("--work-dir", type=project_path, default=DATA_RAW / "work" / "photos")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.export_dir:
            rows, notes = list_export_rows(args.export_dir)
        else:
            connection, notes = open_photos_source(args, "photos")
            try:
                rows, parse_notes = list_screenshot_rows(connection)
            finally:
                connection.close()
            notes.extend(parse_notes)
        write_screenshot_csv(rows, args.out)
    except Exception as exc:  # safety and schema errors are reported, not traced into a deletion path
        return fail(exc)
    emit_notes(notes)
    counts: dict[str, int] = {}
    known_bytes = 0
    bytes_incomplete = False
    for row in rows:
        counts[str(row["asset_class"])] = counts.get(str(row["asset_class"]), 0) + 1
        size = row.get("size_bytes")
        if isinstance(size, int):
            known_bytes += size
        else:
            bytes_incomplete = True
    print(f"rows: {len(rows)}")
    for name in sorted(counts):
        print(f"{name}: {counts[name]}")
    if bytes_incomplete:
        print(f"size_bytes_known: {known_bytes} (incomplete) [unverified]")
    else:
        print(f"size: {format_bytes(known_bytes)}")
    print(f"csv: {args.out}")
    print("Nothing was deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
