"""Guards shared by the local parsers."""

from __future__ import annotations

import re
from pathlib import Path

FILE_ID = re.compile(r"^[0-9a-fA-F]{40}$")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SafetyError(ValueError):
    """The requested path or identifier is outside the read-only local scope."""


class BackupError(RuntimeError):
    """The backup folder cannot be used as-is."""


class EncryptedBackupError(BackupError):
    """Manifest.db is still encrypted, so file contents cannot be read."""


def quote_ident(name: str) -> str:
    if not IDENTIFIER.fullmatch(name):
        raise SafetyError(f"refusing unsafe SQL identifier: {name!r}")
    return f'"{name}"'


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_inside(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    if not is_relative_to(resolved, parent):
        raise SafetyError(f"{label} resolves outside {parent}")
    return resolved


def assert_not_inside(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    if is_relative_to(resolved, parent):
        raise SafetyError(f"{label} must not be written inside {parent}")
    return resolved


def assert_narrow_directory(path: Path, kind: str) -> Path:
    """Refuse to scan the filesystem root or the whole home directory."""
    if not path.exists() or not path.is_dir():
        raise SafetyError(f"{kind} is not a directory: {path}")
    resolved = path.resolve()
    if resolved == Path(resolved.anchor):
        raise SafetyError(f"refusing to treat the filesystem root as a {kind}")
    home = Path.home().resolve()
    if resolved == home:
        raise SafetyError(f"refusing to treat the home directory as a {kind}")
    return resolved


def assert_file_id(file_id: str) -> str:
    if not FILE_ID.fullmatch(file_id):
        raise SafetyError(f"refusing unusual backup file id: {file_id!r}")
    return file_id
