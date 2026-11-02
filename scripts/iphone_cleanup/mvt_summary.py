"""Summarize local mvt-ios JSON. A miss is not a clean bill of health."""

from __future__ import annotations

import json
from pathlib import Path

INDICATOR_KEYS = ("matched_indicators", "matched_indicator", "matched_ioc", "ioc_match")
MAX_JSON_BYTES = 50 * 1024 * 1024
STRING_KEYS = ("type", "value", "name", "indicator", "pattern", "id")


def summarize_mvt_output(directory: Path) -> dict:
    if not directory.is_dir():
        raise FileNotFoundError(f"MVT output directory not found: {directory}")
    files = sorted(path for path in directory.rglob("*.json") if path.is_file())
    notes = [
        "No indicator match does not mean the iPhone is clean. Public IOC feeds "
        "are incomplete, a backup omits artifacts, and a match is a lead to review, "
        "not proof of spyware by itself. [unverified]"
    ]
    if not files:
        notes.append("No JSON files were found in the MVT output directory. The scan cannot be summarized. [unverified]")
        return _result(directory, 0, [], notes, parsed=0, modules_without_hits=[])

    detections: list[dict] = []
    modules_without_hits: list[str] = []
    parsed = 0
    for path in files:
        module = _module_name(path.name)
        if path.stat().st_size > MAX_JSON_BYTES:
            notes.append(f"Skipped {path.name}: larger than {MAX_JSON_BYTES} bytes. [unverified]")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            notes.append(f"Could not parse {path.name}: {exc}. [unverified]")
            continue
        parsed += 1
        found = _collect(payload, path.name, module)
        if found:
            detections.extend(found)
        elif "detected" in path.name.casefold():
            modules_without_hits.append(module)

    deduped = _dedupe(detections)
    if parsed == 0:
        notes.append("Every JSON file failed to parse. Do not treat this as zero detections. [unverified]")
    return _result(
        directory,
        len(deduped),
        deduped,
        notes,
        parsed=parsed,
        modules_without_hits=sorted(set(modules_without_hits)),
    )


def _result(
    directory: Path,
    detection_count: int,
    detections: list[dict],
    notes: list[str],
    parsed: int,
    modules_without_hits: list[str],
) -> dict:
    return {
        "mvt_dir": str(directory),
        "files_parsed": parsed,
        "detection_count": detection_count if parsed else None,
        "detections": detections,
        "modules_with_detection_files_and_no_hits": modules_without_hits,
        "proves_device_clean": False,
        "notes": notes,
    }


def _module_name(filename: str) -> str:
    stem = filename[:-5] if filename.endswith(".json") else filename
    for suffix in ("_detected", "-detected"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _collect(payload: object, filename: str, module: str) -> list[dict]:
    found: list[dict] = []
    _walk(payload, filename, module, found, depth=0)
    return found


def _walk(value: object, filename: str, module: str, found: list[dict], depth: int) -> None:
    if depth > 12:
        return
    if isinstance(value, dict):
        for key in INDICATOR_KEYS:
            if value.get(key):
                found.extend(_normalize(value[key], filename, module))
        for key, child in value.items():
            if key in INDICATOR_KEYS:
                continue
            _walk(child, filename, module, found, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _walk(child, filename, module, found, depth + 1)


def _normalize(value: object, filename: str, module: str) -> list[dict]:
    items = value if isinstance(value, list) else [value]
    normalized: list[dict] = []
    for item in items:
        if isinstance(item, str):
            normalized.append(
                {"file": filename, "module": module, "value": item[:300], "unparsed": False}
            )
            continue
        if not isinstance(item, dict):
            normalized.append(
                {"file": filename, "module": module, "unparsed": True, "keys": []}
            )
            continue
        compact = {"file": filename, "module": module, "unparsed": False}
        for key in STRING_KEYS:
            if key in item and isinstance(item[key], (str, int, float)) and not isinstance(item[key], bool):
                compact[key] = str(item[key])[:300]
        if len(compact) == 3:
            compact["unparsed"] = True
            compact["keys"] = sorted(str(key) for key in item.keys())[:20]
        normalized.append(compact)
    return normalized


def _dedupe(detections: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for item in detections:
        marker = tuple(sorted((key, str(value)) for key, value in item.items()))
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique
