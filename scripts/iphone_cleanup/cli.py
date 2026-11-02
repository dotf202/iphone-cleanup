"""Shared command-line helpers. These commands do not delete or upload."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .backup import BackupError, EncryptedBackupError, connect_readonly, extract_photos_database, open_backup

ROOT = Path(__file__).resolve().parents[2]
DATA_OUT = ROOT / "data" / "out"
DATA_RAW = ROOT / "data" / "raw"


def project_path(value: str) -> Path:
    return Path(value).expanduser()


def add_photos_source(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--backup", type=project_path, help="folder containing Manifest.plist")
    source.add_argument("--photos-sqlite", type=project_path, help="a Photos.sqlite file already copied locally")


def open_photos_source(args: argparse.Namespace, work_name: str) -> tuple[sqlite3.Connection, list[str]]:
    notes: list[str] = []
    if getattr(args, "photos_sqlite", None):
        path = args.photos_sqlite
        if not path.is_file():
            raise BackupError(f"Photos.sqlite not found: {path}")
        return connect_readonly(path), notes
    backup = open_backup(args.backup)
    notes.extend(backup.notes)
    work = getattr(args, "work_dir", None) or (DATA_RAW / "work" / work_name)
    extracted = extract_photos_database(backup, work)
    notes.append(f"Copied Photos.sqlite out of the backup for read-only parsing: {extracted}")
    return connect_readonly(extracted), notes


def emit_notes(notes: list[str]) -> None:
    for note in notes:
        print(note, file=sys.stderr)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def fail(exc: Exception) -> int:
    print(str(exc), file=sys.stderr)
    if isinstance(exc, EncryptedBackupError):
        return 2
    if isinstance(exc, (BackupError, FileNotFoundError, ValueError)):
        return 2
    return 1
