#!/usr/bin/env python3
"""Summarize an mvt-ios output directory. Does not contact the network."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.cli import DATA_OUT, fail, project_path, write_json
from iphone_cleanup.mvt_summary import summarize_mvt_output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize local MVT JSON results.")
    parser.add_argument("--mvt-dir", type=project_path, required=True)
    parser.add_argument("--out", type=project_path, default=DATA_OUT / "spyware_summary.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = summarize_mvt_output(args.mvt_dir)
    except Exception as exc:
        return fail(exc)
    write_json(args.out, summary)
    print(f"files_parsed: {summary['files_parsed']}")
    print(f"detection_count: {summary['detection_count']}")
    print("proves_device_clean: false")
    print(f"json: {args.out}")
    for note in summary["notes"]:
        print(note, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
