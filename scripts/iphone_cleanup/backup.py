"""Read an iOS backup folder without modifying it."""

from __future__ import annotations

import hashlib
import os
import plistlib
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from .safety import (
    BackupError,
    EncryptedBackupError,
    SafetyError,
    assert_file_id,
    assert_narrow_directory,
    assert_not_inside,
)

SQLITE_MAGIC = b"SQLite format 3\x00"
PHOTOS_DOMAIN = "CameraRollDomain"
PHOTOS_RELATIVE_PATH = "Media/PhotoData/Photos.sqlite"

# Copied into reports only when present. Identifiers stay in the backup.
DEVICE_FIELDS = {
    "Device Name": "device_name",
    "Product Type": "product_type",
    "Product Version": "product_version",
    "Build Version": "build_version",
    "Last Backup Date": "last_backup_date",
}

DECRYPT_HINT = """
This backup is encrypted, so its databases cannot be read in place.
Decrypt a local copy with mvt. Let mvt prompt for the password.
Do not put the password on the command line, in an environment variable,
or in a file, and do not write it in the chat or the report.

Check the destination flag first:

  .venv/bin/mvt-ios decrypt-backup --help

Then, with network lookups off, decrypt into the gitignored raw folder
and re-run this command with --backup pointed at that decrypted copy.
""".strip()


@dataclass
class Backup:
    root: Path
    manifest_plist: dict
    info_plist: dict
    encrypted_flag: bool
    manifest_is_sqlite: bool
    notes: list[str] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return self.manifest_is_sqlite


def is_sqlite(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as handle:
        return handle.read(16) == SQLITE_MAGIC


def load_plist(path: Path) -> dict:
    with path.open("rb") as handle:
        data = plistlib.load(handle)
    if not isinstance(data, dict):
        raise BackupError(f"{path.name} is not a plist dictionary")
    return data


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not is_sqlite(path):
        raise BackupError(f"not a SQLite database: {path}")
    uri = "file:{}?mode=ro".format(quote(path.resolve().as_posix()))
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def open_backup(path: Path) -> Backup:
    root = assert_narrow_directory(path, "backup")
    manifest_plist_path = root / "Manifest.plist"
    if not manifest_plist_path.is_file():
        raise BackupError(
            f"no Manifest.plist in {root}. Pass the backup folder itself, "
            "not a parent directory."
        )
    manifest_plist = load_plist(manifest_plist_path)
    info_path = root / "Info.plist"
    info_plist = load_plist(info_path) if info_path.is_file() else {}
    encrypted_flag = bool(manifest_plist.get("IsEncrypted"))
    manifest_db = root / "Manifest.db"
    manifest_is_sqlite = is_sqlite(manifest_db)
    notes: list[str] = []
    if encrypted_flag and manifest_is_sqlite:
        notes.append(
            "Manifest.plist says IsEncrypted, but Manifest.db opened as SQLite. "
            "Treating this folder as a decrypted copy. [unverified]"
        )
    if not manifest_db.exists():
        raise BackupError(f"Manifest.db is missing from {root}")
    if not manifest_is_sqlite:
        if encrypted_flag:
            raise EncryptedBackupError(DECRYPT_HINT)
        raise BackupError(f"Manifest.db is not a SQLite database: {manifest_db}")
    return Backup(
        root=root,
        manifest_plist=manifest_plist,
        info_plist=info_plist,
        encrypted_flag=encrypted_flag,
        manifest_is_sqlite=manifest_is_sqlite,
        notes=notes,
    )


def device_summary(info_plist: dict) -> dict:
    summary: dict[str, str] = {}
    for source_key, output_key in DEVICE_FIELDS.items():
        if source_key not in info_plist:
            continue
        value = info_plist[source_key]
        if hasattr(value, "isoformat"):
            summary[output_key] = value.isoformat()
        else:
            summary[output_key] = str(value)
    return summary


def app_display_names(info_plist: dict) -> dict[str, str]:
    applications = info_plist.get("Applications") or info_plist.get("Installed Applications") or {}
    names: dict[str, str] = {}
    if not isinstance(applications, dict):
        return names
    for bundle_id, meta in applications.items():
        if not isinstance(meta, dict):
            continue
        display = meta.get("CFBundleDisplayName") or meta.get("CFBundleName") or ""
        if isinstance(display, str) and display.strip():
            names[str(bundle_id)] = " ".join(display.split())
    return names


def file_id_for(domain: str, relative_path: str) -> str:
    return hashlib.sha1(f"{domain}-{relative_path}".encode("utf-8")).hexdigest()


def resolve_backup_member(backup_root: Path, file_id: str) -> Path:
    safe_id = assert_file_id(file_id)
    candidate = (backup_root / safe_id[:2] / safe_id).resolve()
    root = backup_root.resolve()
    if root not in candidate.parents:
        raise SafetyError("backup file resolves outside the backup")
    if not candidate.is_file():
        raise FileNotFoundError(f"backup member missing: {safe_id}")
    return candidate


def copy_member(backup_root: Path, file_id: str, destination: Path) -> Path:
    source = resolve_backup_member(backup_root, file_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert_not_inside(destination, backup_root, "extraction destination")
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)
    return destination


def lookup_file(connection: sqlite3.Connection, domain: str, relative_path: str) -> str | None:
    row = connection.execute(
        "SELECT fileID FROM Files WHERE domain = ? AND relativePath = ?",
        (domain, relative_path),
    ).fetchone()
    if row and row["fileID"]:
        return str(row["fileID"])
    digest = file_id_for(domain, relative_path)
    hashed = connection.execute(
        "SELECT fileID FROM Files WHERE fileID = ?",
        (digest,),
    ).fetchone()
    if hashed:
        return digest
    return None


def locate_photos(connection: sqlite3.Connection) -> sqlite3.Row | None:
    rows = connection.execute(
        """
        SELECT domain, relativePath, fileID
        FROM Files
        WHERE relativePath = ?
           OR relativePath LIKE '%/Photos.sqlite'
           OR relativePath LIKE '%Photos.sqlite'
        """,
        (PHOTOS_RELATIVE_PATH,),
    ).fetchall()
    candidates = [
        row
        for row in rows
        if str(row["relativePath"]).endswith("Photos.sqlite")
        and not str(row["relativePath"]).endswith("Photos.sqlite-wal")
        and not str(row["relativePath"]).endswith("Photos.sqlite-shm")
    ]
    if not candidates:
        return None

    def rank(row: sqlite3.Row) -> tuple[int, int]:
        path = str(row["relativePath"])
        domain = str(row["domain"])
        score = 0
        if domain == PHOTOS_DOMAIN:
            score += 10
        if path == PHOTOS_RELATIVE_PATH or path.endswith("PhotoData/Photos.sqlite"):
            score += 5
        return (score, -len(path))

    return max(candidates, key=rank)


def extract_photos_database(backup: Backup, work_dir: Path) -> Path:
    if not backup.readable:
        raise EncryptedBackupError(DECRYPT_HINT)
    connection = connect_readonly(backup.root / "Manifest.db")
    try:
        row = locate_photos(connection)
        if row is None:
            raise BackupError(
                "Photos.sqlite is not in this backup. Export the screenshots "
                "from the Photos app and re-run with --export-dir, or confirm "
                "this is a full backup. [unverified]"
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        assert_not_inside(work_dir, backup.root, "work directory")
        destination = work_dir / "Photos.sqlite"
        copy_member(backup.root, str(row["fileID"]), destination)
        domain = str(row["domain"])
        base = str(row["relativePath"])
        for suffix in ("-wal", "-shm"):
            sidecar_id = lookup_file(connection, domain, base + suffix)
            if sidecar_id is None:
                continue
            try:
                copy_member(backup.root, sidecar_id, work_dir / f"Photos.sqlite{suffix}")
            except FileNotFoundError:
                continue
        return destination
    finally:
        connection.close()
