#!/usr/bin/env python3
"""Count Recently Deleted and hidden photos. Does not empty either album."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.cli import DATA_OUT, DATA_RAW, emit_notes, fail, open_photos_source, project_path, write_json
from iphone_cleanup.photos import deleted_and_hidden_summary
from iphone_cleanup.timestamps import format_bytes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Recently Deleted and hidden counts.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--backup", type=project_path)
    source.add_argument("--photos-sqlite", type=project_path)
    parser.add_argument("--out", type=project_path, default=DATA_OUT / "deleted_photos.json")
    parser.add_argument("--work-dir", type=project_path, default=DATA_RAW / "work" / "photos")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        connection, notes = open_photos_source(args, "photos")
        try:
            summary = deleted_and_hidden_summary(connection)
        finally:
            connection.close()
    except Exception as exc:
        return fail(exc)
    summary["notes"] = notes + summary["notes"]
    summary["source"] = str(args.backup or args.photos_sqlite)
    write_json(args.out, summary)
    counts = summary["counts"]

    def show(value: object) -> str:
        if value is None:
            return "not available [unverified]"
        return str(value)

    print(f"assets: {show(counts['assets'])}")
    print(f"recently_deleted: {show(counts['recently_deleted'])}")
    print(f"hidden: {show(counts['hidden'])}")
    print(f"recently_deleted_size: {format_bytes(summary['recently_deleted_bytes'])}")
    print(f"hidden_size: {format_bytes(summary['hidden_bytes'])}")
    print(f"json: {args.out}")
    print("Nothing was deleted. iCloud copies are not proven gone. [unverified]")
    emit_notes(summary["notes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
