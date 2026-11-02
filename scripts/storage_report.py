#!/usr/bin/env python3
"""Report the largest backup domains and cache-like paths. Deletes nothing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.backup import open_backup
from iphone_cleanup.cli import DATA_OUT, fail, project_path
from iphone_cleanup.storage import summarize_backup, write_storage_reports
from iphone_cleanup.timestamps import format_bytes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize backup storage. Nothing is deleted.")
    parser.add_argument("--backup", type=project_path, required=True)
    parser.add_argument("--out-dir", type=project_path, default=DATA_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        backup = open_backup(args.backup)
        summary = summarize_backup(backup)
        paths = write_storage_reports(summary, args.out_dir)
    except Exception as exc:
        return fail(exc)
    print(f"files: {summary['file_count']}")
    print(f"sized_bytes: {format_bytes(summary['sized_bytes'])}")
    if summary["total_bytes"] is None:
        print("total_bytes: incomplete [unverified]")
    else:
        print(f"total_bytes: {format_bytes(summary['total_bytes'])}")
    print(f"cache_candidate_bytes: {format_bytes(summary['cache_candidate_bytes'])}")
    if summary["domains"]:
        top = summary["domains"][0]
        print(f"largest_domain: {top['domain']} {format_bytes(top['total_bytes'])}")
    print(f"json: {paths['json']}")
    print("Nothing was deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
