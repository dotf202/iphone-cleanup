#!/usr/bin/env python3
"""Print the on-phone checklist. Record a status only when one is passed in."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iphone_cleanup.checklist import fresh_checklist, load_checklist, render_text, save_checklist, set_status
from iphone_cleanup.cli import DATA_OUT, fail, project_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="On-phone checklist. Changes nothing on the iPhone.")
    parser.add_argument("--out", type=project_path, default=DATA_OUT / "device_checklist.json")
    parser.add_argument("--reset", action="store_true", help="set every item back to not_checked")
    parser.add_argument("--set", action="append", default=[], metavar="ID=STATUS")
    parser.add_argument("--note", action="append", default=[], metavar="ID=TEXT")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        data = fresh_checklist() if args.reset else load_checklist(args.out)
        notes = {}
        for item in args.note:
            item_id, separator, text = item.partition("=")
            if not separator:
                raise ValueError(f"--note must look like id=text, got {item!r}")
            notes[item_id] = text
        for item in args.set:
            item_id, separator, status = item.partition("=")
            if not separator:
                raise ValueError(f"--set must look like id=status, got {item!r}")
            set_status(data, item_id, status, notes.pop(item_id, None))
        for item_id, text in notes.items():
            set_status(data, item_id, _status_of(data, item_id), text)
        save_checklist(args.out, data)
    except Exception as exc:
        return fail(exc)
    sys.stdout.write(render_text(data))
    print(f"json: {args.out}")
    return 0


def _status_of(data: dict, item_id: str) -> str:
    for item in data["items"]:
        if item["id"] == item_id:
            return item["status"]
    raise ValueError(f"unknown checklist id: {item_id}")


if __name__ == "__main__":
    sys.exit(main())
