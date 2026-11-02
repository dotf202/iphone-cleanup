"""Core Data timestamps are seconds since 2001-01-01 UTC."""

from __future__ import annotations

from datetime import datetime, timezone

COCOA_OFFSET = 978307200
_UNIX_MAX = 4102444800  # 2100-01-01 UTC


def cocoa_to_utc(value: object) -> str | None:
    if value is None or value == "":
        return None
    try:
        unix = float(value) + COCOA_OFFSET
    except (TypeError, ValueError):
        return None
    if unix < 0 or unix > _UNIX_MAX:
        return None
    return datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_bytes(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(size)
    for unit in ("bytes", "KiB", "MiB", "GiB"):
        if value < 1024:
            if unit == "bytes":
                return f"{int(value)} bytes"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"
