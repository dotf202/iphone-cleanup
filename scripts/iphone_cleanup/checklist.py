"""Manual on-phone checklist. Statuses change only when a command sets them."""

from __future__ import annotations

import json
from pathlib import Path

STATUSES = ("not_checked", "looks_ok", "needs_attention", "unverified")

ITEMS = [
    {
        "id": "configuration_profiles",
        "title": "Configuration profiles, VPN, and device management",
        "where": "Settings > General > VPN & Device Management",
        "look_for": (
            "Any configuration profile, VPN configuration, or device-management "
            "enrollment Taylor does not recognize."
        ),
    },
    {
        "id": "apple_id_devices",
        "title": "Apple ID device list",
        "where": "Settings > [Taylor's name at the top] > device list at the bottom",
        "look_for": (
            "Devices signed in with this Apple ID that Taylor does not recognize. "
            "Removing one is Taylor's tap in Settings. An unknown device is a lead, "
            "not proof of spyware."
        ),
    },
    {
        "id": "safety_check",
        "title": "Safety Check",
        "where": "Settings > Privacy & Security > Safety Check",
        "look_for": (
            "Sharing that looks wrong. Use the review. Do not run Emergency Reset "
            "unless Taylor explicitly asks for that broader reset."
        ),
    },
    {
        "id": "app_permissions",
        "title": "App permissions",
        "where": (
            "Settings > Privacy & Security > Location Services, Photos, Camera, "
            "Microphone, Bluetooth, Local Network, and Contacts"
        ),
        "look_for": (
            "Apps Taylor does not remember allowing, especially Photos Full Access, "
            "Microphone, Camera, and Location set to Always."
        ),
    },
    {
        "id": "unknown_apps",
        "title": "Unknown apps",
        "where": "Home screen, and Settings > General > iPhone Storage",
        "look_for": "Apps Taylor does not recognize. Do not delete them during the inventory.",
    },
    {
        "id": "ios_version",
        "title": "iOS version",
        "where": "Settings > General > About > iOS Version",
        "look_for": (
            "The version Taylor reads aloud. A comparison to Apple's current "
            "release stays unverified until that public page is checked. Updates "
            "are installed by Taylor in Settings > General > Software Update."
        ),
    },
    {
        "id": "lockdown_mode",
        "title": "Lockdown Mode",
        "where": "Settings > Privacy & Security > Lockdown Mode",
        "look_for": (
            "Whether it is on or off. Lockdown Mode is optional protection aimed "
            "at someone who may be personally targeted. It restricts some attachments, "
            "unknown FaceTime calls, wired accessories while locked, configuration "
            "profiles, and some web technologies, and it breaks some sites. "
            "Leave the switch as Taylor found it unless Taylor decides."
        ),
    },
]


def fresh_checklist() -> dict:
    return {
        "instructions": (
            "Set a status only from what Taylor reports after looking at the phone. "
            "Do not guess. not_checked means the item was not reviewed."
        ),
        "items": [
            {
                **item,
                "status": "not_checked",
                "note": "",
            }
            for item in ITEMS
        ],
    }


def load_checklist(path: Path) -> dict:
    if not path.exists():
        data = fresh_checklist()
        save_checklist(path, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    known = {item["id"]: item for item in data.get("items", [])}
    merged = fresh_checklist()
    for item in merged["items"]:
        previous = known.get(item["id"])
        if not previous:
            continue
        status = previous.get("status", "not_checked")
        if status in STATUSES:
            item["status"] = status
        item["note"] = str(previous.get("note") or "")
    return merged


def save_checklist(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_status(data: dict, item_id: str, status: str, note: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    for item in data["items"]:
        if item["id"] == item_id:
            item["status"] = status
            if note is not None:
                item["note"] = note
            return
    raise ValueError(f"unknown checklist id: {item_id}")


def render_text(data: dict) -> str:
    lines = [
        "On-phone checklist. Nothing is changed from the computer.",
        "Statuses: not_checked, looks_ok, needs_attention, unverified.",
        "",
    ]
    for item in data["items"]:
        lines.append(f"- {item['title']} [{item['status']}]")
        lines.append(f"  Where: {item['where']}")
        lines.append(f"  Look for: {item['look_for']}")
        if item.get("note"):
            lines.append(f"  Taylor's note: {item['note']}")
    return "\n".join(lines) + "\n"
