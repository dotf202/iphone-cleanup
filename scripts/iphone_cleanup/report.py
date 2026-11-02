"""Build a BLUF report from local parser outputs. It never deletes anything."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from .timestamps import format_bytes

NOTES_BEGIN = "<!-- session-notes:begin -->"
NOTES_END = "<!-- session-notes:end -->"
DEFAULT_NOTES = "_No session notes yet. Add only statements Taylor made in this session._"


def build_report(
    *,
    out_dir: Path,
    destination: Path,
    generated_at: str | None = None,
) -> str:
    spyware = _read_json(out_dir / "spyware_summary.json")
    deleted = _read_json(out_dir / "deleted_photos.json")
    storage = _read_json(out_dir / "storage_summary.json")
    checklist = _read_json(out_dir / "device_checklist.json")
    screenshots = _read_screenshots(out_dir / "screenshots.csv")
    when = generated_at or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    body = _render(
        when=when,
        spyware=spyware,
        deleted=deleted,
        storage=storage,
        checklist=checklist,
        screenshots=screenshots,
        screenshot_path=out_dir / "screenshots.csv",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    notes = _existing_notes(destination)
    rendered = body.replace("<!--NOTES-->", notes)
    destination.write_text(rendered, encoding="utf-8")
    dated = destination.with_name(
        datetime.now().strftime("%Y%m%d") + "-" + destination.name
    )
    if dated != destination:
        dated.write_text(rendered, encoding="utf-8")
    return rendered


def _existing_notes(destination: Path) -> str:
    if not destination.exists():
        return f"{NOTES_BEGIN}\n{DEFAULT_NOTES}\n{NOTES_END}"
    text = destination.read_text(encoding="utf-8")
    start = text.find(NOTES_BEGIN)
    end = text.find(NOTES_END)
    if start == -1 or end == -1 or end < start:
        return f"{NOTES_BEGIN}\n{DEFAULT_NOTES}\n{NOTES_END}"
    block = text[start : end + len(NOTES_END)]
    return block


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_unreadable": True, "path": str(path)}
    if not isinstance(data, dict):
        return {"_unreadable": True, "path": str(path)}
    return data


def _read_screenshots(path: Path) -> list[dict] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _render(
    *,
    when: str,
    spyware: dict | None,
    deleted: dict | None,
    storage: dict | None,
    checklist: dict | None,
    screenshots: list[dict] | None,
    screenshot_path: Path,
) -> str:
    lines = [
        "# iPhone cleanup — BLUF",
        "",
        f"Generated: {when}. Local files only. Nothing was uploaded.",
        "",
        "## Bottom line",
        "",
        "Nothing was deleted. No photos, apps, profiles, or backup files were removed.",
        "",
    ]
    lines.extend(_bluf_bullets(spyware, deleted, storage, checklist, screenshots, screenshot_path))
    lines.extend(["", "## Spyware", ""])
    lines.extend(_spyware_section(spyware))
    lines.extend(["", "## Screenshots awaiting approval", ""])
    lines.extend(_screenshot_section(screenshots, screenshot_path))
    lines.extend(["", "## Recently Deleted, hidden, and iCloud copies", ""])
    lines.extend(_deleted_section(deleted))
    lines.extend(["", "## Storage", ""])
    lines.extend(_storage_section(storage))
    lines.extend(["", "## Device checklist", ""])
    lines.extend(_checklist_section(checklist))
    lines.extend(
        [
            "",
            "## Unverified",
            "",
            "Anything marked `[unverified]` is a lead or a limit of the backup, not a confirmed fact.",
            "A missing source is reported as not run or not available. It is not reported as zero.",
            "",
            "## Session notes",
            "",
            "<!--NOTES-->",
            "",
        ]
    )
    return "\n".join(lines)


def _bluf_bullets(spyware, deleted, storage, checklist, screenshots, screenshot_path) -> list[str]:
    bullets = []
    if spyware is None:
        bullets.append("- Spyware: not run.")
    elif spyware.get("_unreadable"):
        bullets.append("- Spyware: summary file could not be read. [unverified]")
    else:
        count = spyware.get("detection_count")
        if count is None:
            bullets.append("- Spyware: MVT output could not be summarized. This is not zero detections. [unverified]")
        elif count:
            bullets.append(
                f"- Spyware: MVT recorded {count} indicator match(es). Review them as leads, not proof. [unverified]"
            )
        else:
            bullets.append(
                "- Spyware: MVT recorded no indicator matches in the JSON that parsed. "
                "That does not show the iPhone is clean. [unverified]"
            )
    if screenshots is None:
        bullets.append("- Screenshots: not run.")
    else:
        shots = [row for row in screenshots if row.get("asset_class") == "screenshot"]
        recordings = [row for row in screenshots if row.get("asset_class") == "screen_recording"]
        other = len(screenshots) - len(shots) - len(recordings)
        size = _sum_sizes(shots)
        bullets.append(
            f"- Screenshots: {len(shots)} candidate(s), {format_bytes(size) if size is not None else 'size unknown'}, "
            f"listed in `{screenshot_path}`. Waiting for Taylor's approval. "
            f"Screen recordings in the same file: {len(recordings)}. Other rows: {other}."
        )
    if deleted is None:
        bullets.append("- Recently Deleted and hidden: not run.")
    elif deleted.get("_unreadable"):
        bullets.append("- Recently Deleted and hidden: summary file could not be read. [unverified]")
    else:
        counts = deleted.get("counts") or {}
        bullets.append(
            "- Recently Deleted: "
            + _count_text(counts.get("recently_deleted"))
            + f" ({format_bytes(deleted.get('recently_deleted_bytes'))}). "
            + "Hidden: "
            + _count_text(counts.get("hidden"))
            + ". iCloud copies are not proven gone. [unverified]"
        )
    if storage is None:
        bullets.append("- Storage: not run.")
    elif storage.get("_unreadable"):
        bullets.append("- Storage: summary file could not be read. [unverified]")
    else:
        domains = storage.get("domains") or []
        if domains:
            top = domains[0]
            bullets.append(
                f"- Storage: largest domain `{top.get('domain')}` at "
                f"{format_bytes(top.get('total_bytes'))}. "
                f"Cache-like paths add up to {format_bytes(storage.get('cache_candidate_bytes'))} "
                "and are not a delete list."
            )
        else:
            bullets.append("- Storage: no domain totals were produced. [unverified]")
    if checklist is None:
        bullets.append("- Device checklist: not started.")
    else:
        items = checklist.get("items") or []
        pending = sum(1 for item in items if item.get("status") == "not_checked")
        attention = sum(1 for item in items if item.get("status") == "needs_attention")
        bullets.append(
            f"- Device checklist: {pending} of {len(items)} not checked, {attention} marked needs attention."
        )
    return bullets


def _count_text(value: object) -> str:
    if value is None:
        return "not available [unverified]"
    return str(value)


def _sum_sizes(rows: list[dict]) -> int | None:
    total = 0
    seen = False
    for row in rows:
        raw = row.get("size_bytes")
        if raw in (None, ""):
            continue
        try:
            total += int(raw)
            seen = True
        except (TypeError, ValueError):
            continue
    return total if seen else None


def _spyware_section(spyware: dict | None) -> list[str]:
    if spyware is None:
        return ["Not run. Use `/spyware-scan` on a local decrypted backup."]
    if spyware.get("_unreadable"):
        return ["The summary file could not be read. [unverified]"]
    lines = [
        "This section does not prove the device is clean or compromised. `proves_device_clean` is false.",
        "",
    ]
    count = spyware.get("detection_count")
    if count is None:
        lines.append("Detections: not available, because the output did not parse. [unverified]")
    else:
        lines.append(f"Detections recorded: {count}.")
    for item in (spyware.get("detections") or [])[:30]:
        label = item.get("name") or item.get("type") or item.get("module") or "match"
        value = item.get("value") or item.get("pattern") or item.get("indicator") or ""
        lines.append(
            f"- `{item.get('module', '')}` in `{item.get('file', '')}`: {label} {value}".rstrip()
        )
    extra = len(spyware.get("detections") or []) - 30
    if extra > 0:
        lines.append(f"- {extra} more match(es) remain in the local JSON.")
    quiet = spyware.get("modules_with_detection_files_and_no_hits") or []
    if quiet:
        lines.append("")
        lines.append("Modules with a detection file and no match: " + ", ".join(f"`{name}`" for name in quiet) + ".")
    lines.append("")
    lines.extend(f"- {note}" for note in spyware.get("notes") or [])
    return lines


def _screenshot_section(rows: list[dict] | None, path: Path) -> list[str]:
    if rows is None:
        return ["Not run. Use `/screenshots`."]
    if not rows:
        return [
            f"`{path}` has a header and no rows.",
            "An empty list can mean there were no candidates in the source that was parsed. "
            "It does not by itself describe iCloud or another device. [unverified]",
        ]
    shots = [row for row in rows if row.get("asset_class") == "screenshot"]
    dates = sorted(row.get("created_utc") or "" for row in shots if row.get("created_utc"))
    lines = [
        f"Candidate file: `{path}`.",
        "Do not delete from this list until Taylor approves this exact file.",
        "Rows with trashed_state 1 are already in Recently Deleted.",
        "Rows with asset_class `screen_recording`, `conflicting`, or `export_file` are not part of the screenshot approval.",
    ]
    if dates:
        lines.append(f"Screenshot candidate dates (UTC): {dates[0]} through {dates[-1]}.")
    lines.append(
        "Classification of backup rows is a schema convention. Confirm a sample on the phone. [unverified]"
    )
    return lines


def _deleted_section(deleted: dict | None) -> list[str]:
    if deleted is None:
        return ["Not run. Use `/deleted-photos`."]
    if deleted.get("_unreadable"):
        return ["The summary file could not be read. [unverified]"]
    counts = deleted.get("counts") or {}
    lines = [
        f"Asset table: `{deleted.get('asset_table', 'unknown')}`.",
        f"Assets counted: {_count_text(counts.get('assets'))}.",
        f"Recently Deleted (ZTRASHEDSTATE = 1): {_count_text(counts.get('recently_deleted'))}, "
        f"{format_bytes(deleted.get('recently_deleted_bytes'))}.",
        f"Hidden (ZHIDDEN = 1): {_count_text(counts.get('hidden'))}, "
        f"{format_bytes(deleted.get('hidden_bytes'))}.",
        "A local backup cannot show that an iCloud copy, a Shared Album, a Messages attachment, "
        "or another device's library is gone. [unverified]",
    ]
    oldest = deleted.get("recently_deleted_oldest_utc")
    newest = deleted.get("recently_deleted_newest_utc")
    if oldest or newest:
        lines.append(f"Recently Deleted dates (UTC): {oldest or 'unknown'} through {newest or 'unknown'}.")
    cloud = deleted.get("cloud_columns") or {}
    if cloud:
        lines.append("")
        lines.append("iCloud-related columns were counted and not interpreted:")
        for name, info in cloud.items():
            values = info.get("values") or {}
            rendered = ", ".join(f"{key}={count}" for key, count in sorted(values.items()))
            lines.append(f"- `{name}`: {rendered} [unverified]")
    lines.append("")
    lines.extend(f"- {note}" for note in deleted.get("notes") or [])
    return lines


def _storage_section(storage: dict | None) -> list[str]:
    if storage is None:
        return ["Not run. Use `/storage`."]
    if storage.get("_unreadable"):
        return ["The summary file could not be read. [unverified]"]
    device = storage.get("device") or {}
    lines = []
    if device:
        bits = [f"{key} `{value}`" for key, value in device.items()]
        lines.append("Device fields copied from the backup (identifiers omitted): " + "; ".join(bits) + ".")
    total = storage.get("total_bytes")
    if total is None:
        lines.append(
            f"Sized bytes: {format_bytes(storage.get('sized_bytes'))}. "
            "The full total is withheld because some files had no size. [unverified]"
        )
    else:
        lines.append(f"Total sized bytes: {format_bytes(total)}.")
    lines.append(
        f"Cache-like paths: {storage.get('cache_candidate_files', 0)} file(s), "
        f"{format_bytes(storage.get('cache_candidate_bytes'))}. These are not a delete list."
    )
    lines.append("")
    lines.append("Largest domains:")
    for row in (storage.get("domains") or [])[:15]:
        name = row.get("display_name") or row.get("domain")
        lines.append(
            f"- {name}: {format_bytes(row.get('total_bytes'))} "
            f"({row.get('category')}, cache-like {format_bytes(row.get('cache_bytes'))})"
        )
    lines.append("")
    lines.append("Largest files:")
    for row in (storage.get("largest_files") or [])[:15]:
        cache = " cache-like" if row.get("cache_candidate") else ""
        lines.append(
            f"- {format_bytes(row.get('size_bytes'))}{cache}: `{row.get('domain')}` `{row.get('relative_path')}`"
        )
    lines.append("")
    lines.extend(f"- {note}" for note in storage.get("notes") or [])
    return lines


def _checklist_section(checklist: dict | None) -> list[str]:
    if checklist is None:
        return ["Not started. Use `/device-checklist`. Statuses stay `not_checked` until Taylor answers."]
    lines = []
    for item in checklist.get("items") or []:
        note = f" — {item['note']}" if item.get("note") else ""
        lines.append(f"- {item.get('title')}: `{item.get('status')}`{note}")
    return lines or ["Checklist file had no items. [unverified]"]
