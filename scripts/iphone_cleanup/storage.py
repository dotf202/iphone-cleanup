"""Summarize backup file sizes. Cache hits are leads, not delete instructions."""

from __future__ import annotations

import csv
import plistlib
import sqlite3
from pathlib import Path

from .backup import Backup, app_display_names, connect_readonly, device_summary

TOP_FILES = 50
CACHE_SEGMENTS = {"tmp", "Caches", "fsCachedData", "SplashBoard"}


def extract_size(blob: object) -> int | None:
    if blob is None or blob == b"":
        return None
    if isinstance(blob, bool):
        return None
    if isinstance(blob, int):
        return blob
    if not isinstance(blob, (bytes, bytearray)):
        return None
    try:
        data = plistlib.loads(blob)
    except Exception:
        return None
    if isinstance(data, dict):
        top = data.get("Size")
        if isinstance(top, int) and not isinstance(top, bool):
            return top
    found = _find_int_key(data, "Size")
    return found


def _find_int_key(value: object, key: str) -> int | None:
    if isinstance(value, dict):
        if key in value and isinstance(value[key], int) and not isinstance(value[key], bool):
            return value[key]
        for child in value.values():
            found = _find_int_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_int_key(child, key)
            if found is not None:
                return found
    return None


def is_cache_path(relative_path: str) -> bool:
    parts = [part for part in relative_path.split("/") if part]
    if CACHE_SEGMENTS.intersection(parts):
        return True
    lowered = relative_path.casefold()
    if lowered.endswith("/cache.db") or lowered.endswith("cache.db"):
        return True
    return False


def classify_domain(domain: str) -> tuple[str, str]:
    if domain.startswith("AppDomain-"):
        return "app", domain[len("AppDomain-") :]
    if domain.startswith("AppDomainGroup-"):
        return "app_group", domain[len("AppDomainGroup-") :]
    if domain.startswith("AppDomainPlugin-"):
        return "app_plugin", domain[len("AppDomainPlugin-") :]
    if domain == "CameraRollDomain":
        return "photos", domain
    if domain in {"HomeDomain", "MediaDomain", "RootDomain", "DatabaseDomain"}:
        return "system", domain
    return "other", domain


def summarize_backup(backup: Backup, top_n: int = TOP_FILES) -> dict:
    connection = connect_readonly(backup.root / "Manifest.db")
    try:
        return _summarize(connection, backup, top_n)
    finally:
        connection.close()


def _summarize(connection: sqlite3.Connection, backup: Backup, top_n: int) -> dict:
    notes = list(backup.notes)
    names = app_display_names(backup.info_plist)
    domains: dict[str, dict] = {}
    largest: list[dict] = []
    files = 0
    sized = 0
    unknown = 0
    total = 0
    cache_total = 0
    cache_files = 0

    for row in connection.execute("SELECT domain, relativePath, file FROM Files"):
        files += 1
        domain = str(row["domain"] or "")
        relative_path = str(row["relativePath"] or "")
        size = extract_size(row["file"])
        cache = is_cache_path(relative_path)
        bucket = domains.setdefault(
            domain,
            {
                "domain": domain,
                "category": classify_domain(domain)[0],
                "bundle_id": classify_domain(domain)[1] if classify_domain(domain)[0] != "other" else "",
                "display_name": "",
                "file_count": 0,
                "sized_file_count": 0,
                "total_bytes": 0,
                "cache_bytes": 0,
                "size_incomplete": False,
            },
        )
        kind, label = classify_domain(domain)
        bucket["category"] = kind
        bucket["bundle_id"] = label if kind in {"app", "app_group", "app_plugin"} else ""
        bucket["display_name"] = names.get(label, "")
        bucket["file_count"] += 1
        if size is None:
            unknown += 1
            bucket["size_incomplete"] = True
        else:
            sized += 1
            bucket["sized_file_count"] += 1
            bucket["total_bytes"] += size
            total += size
            if cache:
                bucket["cache_bytes"] += size
                cache_total += size
                cache_files += 1
        if size is not None:
            largest.append(
                {
                    "domain": domain,
                    "relative_path": relative_path,
                    "size_bytes": size,
                    "cache_candidate": cache,
                }
            )

    if files and unknown:
        notes.append(
            f"{unknown} of {files} files have no readable size in Manifest.db. "
            "Totals are incomplete. [unverified]"
        )
    if files == 0:
        notes.append("Manifest.db has no file rows. [unverified]")
    notes.append(
        "Paths marked cache_candidate match cache-like locations. "
        "They may be recreated by iOS and may also hold sign-in state. "
        "Do not delete them from the backup or the phone by hand. [unverified]"
    )

    domain_rows = sorted(domains.values(), key=lambda item: (-item["total_bytes"], item["domain"]))
    largest.sort(key=lambda item: -item["size_bytes"])
    return {
        "device": device_summary(backup.info_plist),
        "file_count": files,
        "sized_file_count": sized,
        "unknown_size_count": unknown,
        "total_bytes": total if unknown == 0 else None,
        "sized_bytes": total,
        "cache_candidate_bytes": cache_total,
        "cache_candidate_files": cache_files,
        "domains": domain_rows,
        "largest_files": largest[:top_n],
        "notes": notes,
    }


def write_storage_reports(summary: dict, out_dir: Path) -> dict[str, Path]:
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "storage_summary.json"
    domain_path = out_dir / "storage_by_domain.csv"
    files_path = out_dir / "storage_largest_files.csv"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with domain_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "domain",
            "category",
            "bundle_id",
            "display_name",
            "file_count",
            "sized_file_count",
            "total_bytes",
            "cache_bytes",
            "size_incomplete",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in summary["domains"]:
            writer.writerow({key: row.get(key, "") for key in fields})
    with files_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["domain", "relative_path", "size_bytes", "cache_candidate"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in summary["largest_files"]:
            writer.writerow(row)
    return {"json": json_path, "domains": domain_path, "files": files_path}
