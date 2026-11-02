"""Read screenshot, Recently Deleted, and hidden counts from Photos.sqlite.

Classifications follow public forensic conventions for the Photos schema.
They are labeled unverified until Taylor confirms a sample on the phone.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

from .safety import IDENTIFIER, SafetyError, assert_narrow_directory, quote_ident
from .timestamps import cocoa_to_utc

SCREENSHOT_TITLES = {"screenshots", "screenshot"}
RECORDING_TITLES = {"screen recordings", "screen recording"}
INTERESTING_TITLES = SCREENSHOT_TITLES | RECORDING_TITLES

FILENAME_SCREENSHOT = re.compile(r"(?i)(?:^|[/\\])(screenshot|screen[\s_-]?shot)\b")
FILENAME_RECORDING = re.compile(r"(?i)(?:^|[/\\])screen[\s_-]?recording\b")
JOIN_TABLE = re.compile(r"^Z_\d+ASSETS$")
ASSET_FK = re.compile(r"^Z_\d+ASSETS$")
ALBUM_FK = re.compile(r"^Z_\d+ALBUMS$")

# Public write-ups map these ZKINDSUBTYPE values. Confirm on this phone.
SCREENSHOT_SUBTYPE = 10
RECORDING_SUBTYPE = 103

CSV_FIELDS = [
    "asset_pk",
    "created_utc",
    "filename",
    "original_filename",
    "directory",
    "relative_path",
    "uniform_type",
    "width",
    "height",
    "size_bytes",
    "size_source",
    "asset_class",
    "albums",
    "trashed_state",
    "hidden",
    "detection_reasons",
    "confidence",
    "unverified_notes",
]

MEDIA_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
    ".mov",
    ".mp4",
    ".m4v",
}

CLASSIFICATION_NOTE = (
    "Screenshot and screen-recording rows use schema conventions "
    "(ZKINDSUBTYPE 10 or 103, a Screenshots album, or a Screenshot filename). "
    "Confirm a sample on the phone before approving any deletion. [unverified]"
)


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def column_names(connection: sqlite3.Connection, table: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [str(row[1]) for row in rows]


def _asset_table(tables: set[str]) -> str | None:
    if "ZASSET" in tables:
        return "ZASSET"
    if "ZGENERICASSET" in tables:
        return "ZGENERICASSET"
    return None


def _normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def album_membership(
    connection: sqlite3.Connection, tables: set[str]
) -> tuple[dict[int, set[str]], list[str]]:
    notes: list[str] = []
    membership: dict[int, set[str]] = {}
    if "ZGENERICALBUM" not in tables:
        notes.append("ZGENERICALBUM is missing, so album membership was not used. [unverified]")
        return membership, notes
    album_columns = set(column_names(connection, "ZGENERICALBUM"))
    if "Z_PK" not in album_columns or "ZTITLE" not in album_columns:
        notes.append("ZGENERICALBUM has no title column. Album membership was skipped. [unverified]")
        return membership, notes

    join_tables = sorted(name for name in tables if JOIN_TABLE.fullmatch(name))
    if not join_tables:
        notes.append(
            "No Z_##ASSETS album-membership table was found. "
            "Album membership was skipped. [unverified]"
        )
        return membership, notes

    used = False
    for join_name in join_tables:
        columns = column_names(connection, join_name)
        asset_cols = [name for name in columns if ASSET_FK.fullmatch(name)]
        album_cols = [name for name in columns if ALBUM_FK.fullmatch(name)]
        if len(asset_cols) != 1 or len(album_cols) != 1:
            continue
        asset_col = quote_ident(asset_cols[0])
        album_col = quote_ident(album_cols[0])
        query = (
            f"SELECT j.{asset_col} AS asset_pk, a.{quote_ident('ZTITLE')} AS title "
            f"FROM {quote_ident(join_name)} AS j "
            f"JOIN {quote_ident('ZGENERICALBUM')} AS a "
            f"ON a.{quote_ident('Z_PK')} = j.{album_col}"
        )
        for row in connection.execute(query):
            if row["asset_pk"] is None or not row["title"]:
                continue
            raw_title = " ".join(str(row["title"]).split())
            if _normalize_title(raw_title) not in INTERESTING_TITLES:
                continue
            membership.setdefault(int(row["asset_pk"]), set()).add(raw_title)
        used = True
    if not used:
        notes.append(
            "Album membership tables did not have the expected columns. "
            "Album membership was skipped. [unverified]"
        )
    return membership, notes


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _filename_flags(names: list[str]) -> tuple[bool, bool]:
    screenshot = False
    recording = False
    for name in names:
        if not name:
            continue
        if FILENAME_RECORDING.search(name):
            recording = True
        if FILENAME_SCREENSHOT.search(name):
            screenshot = True
    return screenshot, recording


def list_screenshot_rows(
    connection: sqlite3.Connection,
) -> tuple[list[dict[str, object]], list[str]]:
    notes = [CLASSIFICATION_NOTE]
    tables = table_names(connection)
    asset_table = _asset_table(tables)
    if asset_table is None:
        raise SafetyError(
            "Photos.sqlite has neither ZASSET nor ZGENERICASSET. "
            "This schema is unsupported. [unverified]"
        )
    asset_columns = column_names(connection, asset_table)
    if "Z_PK" not in asset_columns:
        raise SafetyError(f"{asset_table} has no Z_PK column. [unverified]")

    wanted = [
        "Z_PK",
        "ZKIND",
        "ZKINDSUBTYPE",
        "ZISDETECTEDSCREENSHOT",
        "ZFILENAME",
        "ZDIRECTORY",
        "ZDATECREATED",
        "ZWIDTH",
        "ZHEIGHT",
        "ZUNIFORMTYPEIDENTIFIER",
        "ZTRASHEDSTATE",
        "ZHIDDEN",
        "ZADDITIONALATTRIBUTES",
    ]
    selected = [name for name in wanted if name in asset_columns]
    missing = [name for name in ("ZKINDSUBTYPE", "ZFILENAME", "ZDATECREATED", "ZTRASHEDSTATE", "ZHIDDEN") if name not in asset_columns]
    for name in missing:
        notes.append(f"{asset_table}.{name} is missing. Related fields are blank. [unverified]")

    membership, album_notes = album_membership(connection, tables)
    notes.extend(album_notes)

    attr_join = _attribute_join(connection, tables, asset_columns)
    cloud_join = _cloud_join(connection, tables, attr_join)
    sql, extra_notes = _asset_query(asset_table, selected, attr_join, cloud_join)
    notes.extend(extra_notes)

    rows: list[dict[str, object]] = []
    for record in connection.execute(sql):
        built = _classify_record(record, asset_columns, membership, attr_join, cloud_join)
        if built is not None:
            rows.append(built)

    rows.sort(
        key=lambda item: (
            not item["created_utc"],
            str(item["created_utc"] or ""),
            -(item["size_bytes"] or 0),
        )
    )
    return rows, notes


def _attribute_join(
    connection: sqlite3.Connection, tables: set[str], asset_columns: list[str]
) -> dict | None:
    if "ZADDITIONALASSETATTRIBUTES" not in tables:
        return None
    columns = column_names(connection, "ZADDITIONALASSETATTRIBUTES")
    if "ZADDITIONALATTRIBUTES" in asset_columns and "Z_PK" in columns:
        return {
            "fk_on": "asset",
            "asset_column": "ZADDITIONALATTRIBUTES",
            "attr_column": "Z_PK",
            "columns": columns,
        }
    if "ZASSET" in columns:
        return {
            "fk_on": "attributes",
            "asset_column": "Z_PK",
            "attr_column": "ZASSET",
            "columns": columns,
        }
    return None


def _cloud_join(
    connection: sqlite3.Connection, tables: set[str], attr_join: dict | None
) -> dict | None:
    if attr_join is None or "ZCLOUDMASTER" not in tables:
        return None
    columns = column_names(connection, "ZCLOUDMASTER")
    if "Z_PK" not in columns:
        return None
    fk = next((name for name in ("ZMASTER", "ZCLOUDMASTER") if name in attr_join["columns"]), None)
    if fk is None:
        return None
    return {"fk": fk, "columns": columns}


def _asset_query(
    asset_table: str,
    selected: list[str],
    attr_join: dict | None,
    cloud_join: dict | None,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    pieces = [f"a.{quote_ident(name)} AS {quote_ident('a_' + name)}" for name in selected]
    joins = []
    if attr_join:
        for name in ("ZORIGINALFILESIZE", "ZORIGINALFILENAME"):
            if name in attr_join["columns"]:
                pieces.append(f"attr.{quote_ident(name)} AS {quote_ident('attr_' + name)}")
        if "ZORIGINALFILESIZE" not in attr_join["columns"]:
            notes.append("ZORIGINALFILESIZE is missing. Sizes may be blank. [unverified]")
        joins.append(
            "LEFT JOIN {attr} AS attr ON attr.{attr_col} = a.{asset_col}".format(
                attr=quote_ident("ZADDITIONALASSETATTRIBUTES"),
                attr_col=quote_ident(attr_join["attr_column"]),
                asset_col=quote_ident(attr_join["asset_column"]),
            )
        )
    else:
        notes.append("Could not join ZADDITIONALASSETATTRIBUTES. Sizes may be blank. [unverified]")
    if cloud_join:
        for name in ("ZORIGINALFILENAME", "ZUNIFORMTYPEIDENTIFIER"):
            if name in cloud_join["columns"]:
                pieces.append(f"cloud.{quote_ident(name)} AS {quote_ident('cloud_' + name)}")
        joins.append(
            "LEFT JOIN {cloud} AS cloud ON cloud.{pk} = attr.{fk}".format(
                cloud=quote_ident("ZCLOUDMASTER"),
                pk=quote_ident("Z_PK"),
                fk=quote_ident(cloud_join["fk"]),
            )
        )
    sql = "SELECT {cols} FROM {asset} AS a {joins}".format(
        cols=", ".join(pieces),
        asset=quote_ident(asset_table),
        joins=" ".join(joins),
    )
    return sql, notes


def _classify_record(
    record: sqlite3.Row,
    asset_columns: list[str],
    membership: dict[int, set[str]],
    attr_join: dict | None,
    cloud_join: dict | None,
) -> dict[str, object] | None:
    keys = set(record.keys())
    asset_pk = record["a_Z_PK"]
    subtype = record["a_ZKINDSUBTYPE"] if "a_ZKINDSUBTYPE" in keys else None
    detected = record["a_ZISDETECTEDSCREENSHOT"] if "a_ZISDETECTEDSCREENSHOT" in keys else None
    filename = record["a_ZFILENAME"] if "a_ZFILENAME" in keys else None
    directory = record["a_ZDIRECTORY"] if "a_ZDIRECTORY" in keys else None
    original_names = []
    if "cloud_ZORIGINALFILENAME" in keys and record["cloud_ZORIGINALFILENAME"]:
        original_names.append(str(record["cloud_ZORIGINALFILENAME"]))
    if "attr_ZORIGINALFILENAME" in keys and record["attr_ZORIGINALFILENAME"]:
        original_names.append(str(record["attr_ZORIGINALFILENAME"]))
    display_original = original_names[0] if original_names else ""
    names_for_match = [str(filename or "")] + original_names
    name_screenshot, name_recording = _filename_flags(names_for_match)

    titles = membership.get(int(asset_pk), set()) if asset_pk is not None else set()
    normalized_titles = {_normalize_title(title) for title in titles}
    in_screenshots = bool(normalized_titles & SCREENSHOT_TITLES)
    in_recordings = bool(normalized_titles & RECORDING_TITLES)

    reasons: list[str] = []
    screenshot_signal = False
    recording_signal = False
    if detected not in (None, 0, "0"):
        reasons.append("z_is_detected_screenshot")
        screenshot_signal = True
    if subtype == SCREENSHOT_SUBTYPE:
        reasons.append("kind_subtype_10")
        screenshot_signal = True
    if subtype == RECORDING_SUBTYPE:
        reasons.append("kind_subtype_103_screen_recording")
        recording_signal = True
    if in_screenshots:
        reasons.append("album_screenshots")
        screenshot_signal = True
    if in_recordings:
        reasons.append("album_screen_recordings")
        recording_signal = True
    if name_screenshot:
        reasons.append("filename_screenshot")
        screenshot_signal = True
    if name_recording:
        reasons.append("filename_screen_recording")
        recording_signal = True
    if not reasons:
        return None

    row_notes: list[str] = []
    if screenshot_signal and recording_signal:
        asset_class = "conflicting"
        row_notes.append("screenshot and screen-recording signals disagree [unverified]")
    elif recording_signal:
        asset_class = "screen_recording"
    else:
        asset_class = "screenshot"

    strong = {
        "z_is_detected_screenshot",
        "kind_subtype_10",
        "kind_subtype_103_screen_recording",
        "album_screenshots",
        "album_screen_recordings",
    }
    confidence = "high" if strong.intersection(reasons) else "medium"
    if asset_class == "conflicting":
        row_notes.append("do not delete until Taylor identifies the file [unverified]")

    size = None
    size_source = ""
    if "attr_ZORIGINALFILESIZE" in keys:
        size = _optional_int(record["attr_ZORIGINALFILESIZE"])
        if size is not None:
            size_source = "ZORIGINALFILESIZE"
    if size is None:
        row_notes.append("size unavailable [unverified]")

    created = cocoa_to_utc(record["a_ZDATECREATED"]) if "a_ZDATECREATED" in keys else None
    if "ZDATECREATED" in asset_columns and created is None and record["a_ZDATECREATED"] not in (None, ""):
        row_notes.append("created date could not be decoded [unverified]")

    uniform = ""
    if "a_ZUNIFORMTYPEIDENTIFIER" in keys and record["a_ZUNIFORMTYPEIDENTIFIER"]:
        uniform = str(record["a_ZUNIFORMTYPEIDENTIFIER"])
    elif "cloud_ZUNIFORMTYPEIDENTIFIER" in keys and record["cloud_ZUNIFORMTYPEIDENTIFIER"]:
        uniform = str(record["cloud_ZUNIFORMTYPEIDENTIFIER"])

    relative = ""
    if directory and filename:
        relative = f"{directory}/{filename}"
    elif filename:
        relative = str(filename)

    trashed = ""
    if "a_ZTRASHEDSTATE" in keys and record["a_ZTRASHEDSTATE"] is not None:
        trashed = str(record["a_ZTRASHEDSTATE"])
    hidden = ""
    if "a_ZHIDDEN" in keys and record["a_ZHIDDEN"] is not None:
        hidden = str(record["a_ZHIDDEN"])

    return {
        "asset_pk": "" if asset_pk is None else str(asset_pk),
        "created_utc": created or "",
        "filename": "" if filename is None else str(filename),
        "original_filename": display_original,
        "directory": "" if directory is None else str(directory),
        "relative_path": relative,
        "uniform_type": uniform,
        "width": "" if "a_ZWIDTH" not in keys or record["a_ZWIDTH"] is None else str(record["a_ZWIDTH"]),
        "height": "" if "a_ZHEIGHT" not in keys or record["a_ZHEIGHT"] is None else str(record["a_ZHEIGHT"]),
        "size_bytes": size,
        "size_source": size_source,
        "asset_class": asset_class,
        "albums": "; ".join(sorted(titles)),
        "trashed_state": trashed,
        "hidden": hidden,
        "detection_reasons": "|".join(reasons),
        "confidence": confidence,
        "unverified_notes": "; ".join(row_notes),
    }


def write_screenshot_csv(rows: list[dict[str, object]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})


def list_export_rows(export_dir: Path) -> tuple[list[dict[str, object]], list[str]]:
    root = assert_narrow_directory(export_dir, "Photos export")
    notes = [
        "Every file in the export folder is listed because it was exported, "
        "not because Photos.sqlite classified it. [unverified]",
        "Dates are filesystem modification times, not capture times. [unverified]",
    ]
    rows: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        stat = path.stat()
        name_screenshot, name_recording = _filename_flags([path.name])
        reasons = ["export_folder"]
        row_notes = ["included because it is in the export folder [unverified]"]
        suffix = path.suffix.casefold()
        if suffix not in MEDIA_SUFFIXES:
            row_notes.append(f"extension {suffix or '(none)'} is not a known photo or video type [unverified]")
        if name_recording:
            reasons.append("filename_screen_recording")
            asset_class = "screen_recording"
            confidence = "medium"
        elif name_screenshot:
            reasons.append("filename_screenshot")
            asset_class = "screenshot"
            confidence = "medium"
        else:
            asset_class = "export_file"
            confidence = "low"
        created_utc = _unix_utc(stat.st_mtime)
        rows.append(
            {
                "asset_pk": "",
                "created_utc": created_utc,
                "filename": path.name,
                "original_filename": path.name,
                "directory": str(path.parent.relative_to(root)),
                "relative_path": str(path.relative_to(root)),
                "uniform_type": suffix.lstrip("."),
                "width": "",
                "height": "",
                "size_bytes": stat.st_size,
                "size_source": "export_filesize",
                "asset_class": asset_class,
                "albums": "",
                "trashed_state": "",
                "hidden": "",
                "detection_reasons": "|".join(reasons),
                "confidence": confidence,
                "unverified_notes": "; ".join(row_notes),
            }
        )
    rows.sort(key=lambda item: (str(item["created_utc"]), -(item["size_bytes"] or 0)))
    return rows, notes


def _unix_utc(timestamp: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def deleted_and_hidden_summary(connection: sqlite3.Connection) -> dict:
    tables = table_names(connection)
    asset_table = _asset_table(tables)
    if asset_table is None:
        raise SafetyError(
            "Photos.sqlite has neither ZASSET nor ZGENERICASSET. [unverified]"
        )
    columns = set(column_names(connection, asset_table))
    notes = [
        "Recently Deleted here means ZTRASHEDSTATE = 1 in this database only. "
        "It does not prove an iCloud copy, a copy on another device, or a "
        "Messages attachment is gone. [unverified]"
    ]
    if "ZTRASHEDSTATE" not in columns:
        notes.append(
            "ZTRASHEDSTATE is missing. Recently Deleted was not counted. "
            "A missing column is not a count of zero. [unverified]"
        )
    if "ZHIDDEN" not in columns:
        notes.append("ZHIDDEN is missing. Hidden items were not counted. [unverified]")

    attr_join = _attribute_join(connection, tables, list(columns))
    size_expr = "NULL"
    joins = ""
    if attr_join and "ZORIGINALFILESIZE" in attr_join["columns"]:
        size_expr = "attr.ZORIGINALFILESIZE"
        joins = (
            "LEFT JOIN {attr} AS attr ON attr.{attr_col} = a.{asset_col}".format(
                attr=quote_ident("ZADDITIONALASSETATTRIBUTES"),
                attr_col=quote_ident(attr_join["attr_column"]),
                asset_col=quote_ident(attr_join["asset_column"]),
            )
        )
    else:
        notes.append("File sizes for deleted or hidden items are incomplete. [unverified]")

    selected = ["a.Z_PK AS asset_pk"]
    if "ZTRASHEDSTATE" in columns:
        selected.append("a.ZTRASHEDSTATE AS trashed_state")
    if "ZHIDDEN" in columns:
        selected.append("a.ZHIDDEN AS hidden")
    if "ZDATECREATED" in columns:
        selected.append("a.ZDATECREATED AS created")
    selected.append(f"{size_expr} AS size_bytes")
    sql = "SELECT {cols} FROM {asset} AS a {joins}".format(
        cols=", ".join(selected),
        asset=quote_ident(asset_table),
        joins=joins,
    )

    assets = 0
    recently_deleted = 0 if "ZTRASHEDSTATE" in columns else None
    hidden = 0 if "ZHIDDEN" in columns else None
    both = 0 if "ZTRASHEDSTATE" in columns and "ZHIDDEN" in columns else None
    other_trashed: dict[str, int] = {}
    deleted_bytes = 0
    hidden_bytes = 0
    deleted_bytes_known = True
    hidden_bytes_known = True
    deleted_dates: list[str] = []

    for record in connection.execute(sql):
        assets += 1
        size = _optional_int(record["size_bytes"]) if "size_bytes" in record.keys() else None
        is_deleted = False
        is_hidden = False
        if "trashed_state" in record.keys() and record["trashed_state"] not in (None,):
            state = _optional_int(record["trashed_state"])
            if state == 1:
                is_deleted = True
                recently_deleted = (recently_deleted or 0) + 1
                if size is None:
                    deleted_bytes_known = False
                else:
                    deleted_bytes += size
                created = cocoa_to_utc(record["created"]) if "created" in record.keys() else None
                if created:
                    deleted_dates.append(created)
            elif state not in (None, 0):
                key = str(state)
                other_trashed[key] = other_trashed.get(key, 0) + 1
        if "hidden" in record.keys() and _optional_int(record["hidden"]) == 1:
            is_hidden = True
            hidden = (hidden or 0) + 1
            if size is None:
                hidden_bytes_known = False
            else:
                hidden_bytes += size
        if both is not None and is_deleted and is_hidden:
            both += 1

    if other_trashed:
        notes.append(
            "Some rows have ZTRASHEDSTATE other than 0 or 1: "
            + ", ".join(f"{key}={count}" for key, count in sorted(other_trashed.items()))
            + ". Those values were not counted as Recently Deleted. [unverified]"
        )

    cloud: dict[str, dict] = {}
    for name in sorted(columns):
        if "CLOUD" not in name:
            continue
        if not IDENTIFIER.fullmatch(name):
            continue
        counts: dict[str, int] = {}
        query = (
            f"SELECT {quote_ident(name)} AS value, COUNT(*) AS n "
            f"FROM {quote_ident(asset_table)} GROUP BY {quote_ident(name)}"
        )
        for row in connection.execute(query):
            value = row["value"]
            if value is None:
                key = "null"
            elif isinstance(value, (bytes, bytearray)):
                key = "blob"
            else:
                key = str(value)
            counts[key] = int(row["n"])
        cloud[name] = {
            "present": True,
            "values": counts,
            "meaning": "unverified",
        }
    if not cloud:
        notes.append(
            "No iCloud state columns were found on the asset table. "
            "iCloud copies cannot be assessed from this file. [unverified]"
        )
    else:
        notes.append(
            "iCloud column values are counted only. Their numeric meanings "
            "depend on the iOS version and are unverified. [unverified]"
        )

    return {
        "asset_table": asset_table,
        "counts": {
            "assets": assets,
            "recently_deleted": recently_deleted,
            "hidden": hidden,
            "hidden_and_recently_deleted": both,
        },
        "recently_deleted_bytes": None if recently_deleted is None or not deleted_bytes_known else deleted_bytes,
        "hidden_bytes": None if hidden is None or not hidden_bytes_known else hidden_bytes,
        "recently_deleted_oldest_utc": min(deleted_dates) if deleted_dates else None,
        "recently_deleted_newest_utc": max(deleted_dates) if deleted_dates else None,
        "other_trashed_states": other_trashed,
        "cloud_columns": cloud,
        "notes": notes,
    }
