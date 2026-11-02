#!/usr/bin/env python3
"""Write the combined BLUF report from local outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.cli import DATA_OUT, ROOT, fail, project_path
from iphone_cleanup.report import build_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a local BLUF report. Nothing is deleted.")
    parser.add_argument("--out-dir", type=project_path, default=DATA_OUT)
    parser.add_argument(
        "--out",
        type=project_path,
        default=ROOT / "reports" / "iphone-cleanup-bluf.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build_report(out_dir=args.out_dir, destination=args.out)
    except Exception as exc:
        return fail(exc)
    print(f"report: {args.out}")
    print("Nothing was deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
