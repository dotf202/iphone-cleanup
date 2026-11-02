"""Parser tests use synthetic databases only. No personal data."""

from __future__ import annotations

import json
import plistlib
import sqlite3
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from iphone_cleanup.backup import (  # noqa: E402
    copy_member,
    device_summary,
    file_id_for,
    load_plist,
    open_backup,
    resolve_backup_member,
)
from iphone_cleanup.checklist import ITEMS  # noqa: E402
from iphone_cleanup.mvt_summary import summarize_mvt_output  # noqa: E402
from iphone_cleanup.photos import (  # noqa: E402
    deleted_and_hidden_summary,
    list_export_rows,
    list_screenshot_rows,
)
from iphone_cleanup.report import NOTES_BEGIN, NOTES_END, build_report  # noqa: E402
from iphone_cleanup.safety import SafetyError  # noqa: E402
from iphone_cleanup.storage import extract_size, is_cache_path, summarize_backup  # noqa: E402
from iphone_cleanup.timestamps import cocoa_to_utc, format_bytes  # noqa: E402

PYTHON = sys.executable


def cocoa(year: int, month: int, day: int) -> int:
    unix = datetime(year, month, day, tzinfo=timezone.utc).timestamp()
    return int(unix - 978307200)


class TimestampTests(unittest.TestCase):
    def test_cocoa_epoch_and_known_day(self):
        self.assertEqual(cocoa_to_utc(0), "2001-01-01T00:00:00Z")
        self.assertEqual(cocoa_to_utc(cocoa(2024, 1, 1)), "2024-01-01T00:00:00Z")
        self.assertIsNone(cocoa_to_utc("not-a-date"))

    def test_format_bytes(self):
        self.assertEqual(format_bytes(None), "unknown")
        self.assertEqual(format_bytes(500), "500 bytes")
        self.assertEqual(format_bytes(2048), "2.0 KiB")


class PhotoParserTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(self.id().replace(".", "_") + ".sqlite")
        # Keep the fixture next to the test process temp via TemporaryDirectory-like path.
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "Photos.sqlite"

    def _base(self, with_trashed: bool = True) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        columns = [
            "Z_PK INTEGER PRIMARY KEY",
            "ZKIND INTEGER",
            "ZKINDSUBTYPE INTEGER",
            "ZISDETECTEDSCREENSHOT INTEGER",
            "ZFILENAME TEXT",
            "ZDIRECTORY TEXT",
            "ZDATECREATED FLOAT",
            "ZWIDTH INTEGER",
            "ZHEIGHT INTEGER",
            "ZUNIFORMTYPEIDENTIFIER TEXT",
            "ZHIDDEN INTEGER",
            "ZADDITIONALATTRIBUTES INTEGER",
        ]
        if with_trashed:
            columns.append("ZTRASHEDSTATE INTEGER")
        connection.execute(f"CREATE TABLE ZASSET ({', '.join(columns)})")
        connection.execute(
            """
            CREATE TABLE ZADDITIONALASSETATTRIBUTES (
                Z_PK INTEGER PRIMARY KEY,
                ZORIGINALFILESIZE INTEGER,
                ZORIGINALFILENAME TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE ZCLOUDMASTER (
                Z_PK INTEGER PRIMARY KEY,
                ZORIGINALFILENAME TEXT,
                ZUNIFORMTYPEIDENTIFIER TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE ZGENERICALBUM (
                Z_PK INTEGER PRIMARY KEY,
                ZTITLE TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE Z_28ASSETS (
                Z_28ASSETS INTEGER,
                Z_3ALBUMS INTEGER
            )
            """
        )
        connection.execute("INSERT INTO ZGENERICALBUM (Z_PK, ZTITLE) VALUES (1, 'Screenshots')")
        connection.execute("INSERT INTO ZGENERICALBUM (Z_PK, ZTITLE) VALUES (2, 'Recents')")
        return connection

    def test_classifies_screenshots_and_leaves_ordinary_photos_out(self):
        connection = self._base()
        created = cocoa(2024, 5, 2)
        rows = [
            # pk, kind, subtype, detected, filename, directory, created, w, h, uti, hidden, attr, trashed
            (1, 0, 10, 0, "IMG_0001.PNG", "DCIM/100APPLE", created, 1170, 2532, "public.png", 0, 11, 0),
            (2, 0, 0, 0, "IMG_0002.HEIC", "DCIM/100APPLE", created, 100, 100, "public.heic", 0, 12, 0),
            (3, 0, 0, 0, "IMG_0003.PNG", "DCIM/100APPLE", cocoa(2023, 1, 1), 10, 10, "public.png", 0, 13, 0),
            (4, 0, 10, 1, "IMG_0004.PNG", "DCIM/100APPLE", cocoa(2024, 6, 1), 50, 50, "public.png", 0, 14, 1),
            (5, 0, 0, 0, "IMG_0005.HEIC", "DCIM/100APPLE", created, 20, 20, "public.heic", 1, 15, 0),
            (6, 1, 103, 0, "IMG_0006.MOV", "DCIM/100APPLE", created, 0, 0, "public.mpeg-4", 0, 16, 0),
        ]
        connection.executemany(
            """
            INSERT INTO ZASSET (
                Z_PK, ZKIND, ZKINDSUBTYPE, ZISDETECTEDSCREENSHOT, ZFILENAME, ZDIRECTORY,
                ZDATECREATED, ZWIDTH, ZHEIGHT, ZUNIFORMTYPEIDENTIFIER, ZHIDDEN,
                ZADDITIONALATTRIBUTES, ZTRASHEDSTATE
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.execute(
            "INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (11, 1200, NULL)"
        )
        connection.execute(
            "INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (13, 80, 'Screenshot 2023-01-01 at 1.02.03 PM.png')"
        )
        connection.execute(
            "INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (14, 4096, NULL)"
        )
        connection.execute("INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (15, 512, NULL)")
        connection.execute("INSERT INTO Z_28ASSETS VALUES (1, 1)")
        connection.commit()
        connection.close()

        read = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        read.row_factory = sqlite3.Row
        listed, notes = list_screenshot_rows(read)
        summary = deleted_and_hidden_summary(read)
        read.close()

        by_pk = {row["asset_pk"]: row for row in listed}
        self.assertIn("1", by_pk)
        self.assertNotIn("2", by_pk)
        self.assertEqual(by_pk["1"]["asset_class"], "screenshot")
        self.assertEqual(by_pk["1"]["confidence"], "high")
        self.assertEqual(by_pk["1"]["size_bytes"], 1200)
        self.assertIn("Screenshots", by_pk["1"]["albums"])
        self.assertEqual(by_pk["1"]["created_utc"], "2024-05-02T00:00:00Z")
        self.assertEqual(by_pk["3"]["confidence"], "medium")
        self.assertIn("filename_screenshot", by_pk["3"]["detection_reasons"])
        self.assertEqual(by_pk["4"]["trashed_state"], "1")
        self.assertNotIn("5", by_pk)
        self.assertEqual(by_pk["6"]["asset_class"], "screen_recording")
        self.assertTrue(any("[unverified]" in note for note in notes))

        self.assertEqual(summary["counts"]["assets"], 6)
        self.assertEqual(summary["counts"]["recently_deleted"], 1)
        self.assertEqual(summary["counts"]["hidden"], 1)
        self.assertEqual(summary["counts"]["hidden_and_recently_deleted"], 0)
        self.assertEqual(summary["recently_deleted_bytes"], 4096)
        self.assertEqual(summary["cloud_columns"], {})
        self.assertTrue(any("iCloud" in note for note in summary["notes"]))

    def test_missing_trashed_column_is_not_a_zero_count(self):
        connection = self._base(with_trashed=False)
        connection.execute(
            """
            INSERT INTO ZASSET (
                Z_PK, ZKIND, ZKINDSUBTYPE, ZISDETECTEDSCREENSHOT, ZFILENAME, ZDIRECTORY,
                ZDATECREATED, ZWIDTH, ZHEIGHT, ZUNIFORMTYPEIDENTIFIER, ZHIDDEN, ZADDITIONALATTRIBUTES
            ) VALUES (1, 0, 0, 0, 'IMG_0001.HEIC', 'DCIM', ?, 1, 1, 'public.heic', 0, NULL)
            """,
            (cocoa(2024, 1, 2),),
        )
        connection.execute(
            """
            ALTER TABLE ZASSET ADD COLUMN ZCLOUDDELETESTATE INTEGER
            """
        )
        connection.execute("UPDATE ZASSET SET ZCLOUDDELETESTATE = 1 WHERE Z_PK = 1")
        connection.commit()
        connection.close()
        read = sqlite3.connect(self.db_path)
        read.row_factory = sqlite3.Row
        summary = deleted_and_hidden_summary(read)
        read.close()
        self.assertIsNone(summary["counts"]["recently_deleted"])
        self.assertEqual(summary["counts"]["hidden"], 0)
        self.assertEqual(summary["cloud_columns"]["ZCLOUDDELETESTATE"]["meaning"], "unverified")
        self.assertIn("1", summary["cloud_columns"]["ZCLOUDDELETESTATE"]["values"])
        self.assertTrue(any("not a count of zero" in note for note in summary["notes"]))

    def test_export_folder_lists_files_and_refuses_home(self):
        import tempfile

        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: None)
        (folder / "Screenshot 2024.png").write_bytes(b"png")
        (folder / "vacation.jpg").write_bytes(b"jpg-bytes")
        (folder / ".hidden.png").write_bytes(b"nope")
        rows, notes = list_export_rows(folder)
        names = {row["filename"] for row in rows}
        self.assertEqual(names, {"Screenshot 2024.png", "vacation.jpg"})
        classes = {row["filename"]: row["asset_class"] for row in rows}
        self.assertEqual(classes["Screenshot 2024.png"], "screenshot")
        self.assertEqual(classes["vacation.jpg"], "export_file")
        self.assertTrue(any("[unverified]" in note for note in notes))
        with self.assertRaises(SafetyError):
            list_export_rows(Path.home())
        with self.assertRaises(SafetyError):
            list_export_rows(Path("/"))


class BackupAndStorageTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _member(self, domain: str, relative_path: str, payload: bytes) -> str:
        file_id = file_id_for(domain, relative_path)
        folder = self.backup / file_id[:2]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / file_id).write_bytes(payload)
        return file_id

    def _write_plists(self, encrypted: bool, info: dict | None = None) -> None:
        self.backup = self.root / "backup"
        self.backup.mkdir()
        with (self.backup / "Manifest.plist").open("wb") as handle:
            plistlib.dump({"IsEncrypted": encrypted, "Version": "3.0"}, handle)
        with (self.backup / "Info.plist").open("wb") as handle:
            plistlib.dump(
                info
                or {
                    "Device Name": "Taylor's iPhone",
                    "Product Version": "18.6",
                    "Product Type": "iPhone16,1",
                    "Serial Number": "SECRET-SERIAL",
                    "IMEI": "SECRET-IMEI",
                    "Applications": {
                        "com.example.maps": {"CFBundleDisplayName": "Example Maps"},
                    },
                },
                handle,
            )

    def test_device_summary_drops_identifiers(self):
        self._write_plists(False)
        summary = device_summary(load_plist(self.backup / "Info.plist"))
        self.assertEqual(summary["product_version"], "18.6")
        self.assertNotIn("SECRET-SERIAL", json.dumps(summary))
        self.assertNotIn("SECRET-IMEI", json.dumps(summary))

    def test_encrypted_backup_refuses_to_parse(self):
        self._write_plists(True)
        (self.backup / "Manifest.db").write_bytes(b"this is not sqlite")
        with self.assertRaises(Exception) as caught:
            open_backup(self.backup)
        self.assertIn("encrypted", str(caught.exception).casefold())
        self.assertNotIn("SECRET", str(caught.exception))
        completed = subprocess.run(
            [PYTHON, str(SCRIPTS / "screenshots.py"), "--backup", str(self.backup)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("encrypted", completed.stderr.casefold())
        self.assertNotIn("SECRET", completed.stderr)
        self.assertNotIn("BACKUP_PASSWORD", completed.stderr)

    def test_storage_and_photo_copy_stay_read_only(self):
        self._write_plists(False)
        photos = self.root / "library.sqlite"
        connection = sqlite3.connect(photos)
        connection.execute(
            """
            CREATE TABLE ZASSET (
                Z_PK INTEGER PRIMARY KEY,
                ZKINDSUBTYPE INTEGER,
                ZFILENAME TEXT,
                ZDIRECTORY TEXT,
                ZDATECREATED FLOAT,
                ZTRASHEDSTATE INTEGER,
                ZHIDDEN INTEGER,
                ZADDITIONALATTRIBUTES INTEGER
            )
            """
        )
        connection.execute(
            "CREATE TABLE ZADDITIONALASSETATTRIBUTES (Z_PK INTEGER PRIMARY KEY, ZORIGINALFILESIZE INTEGER)"
        )
        connection.execute(
            "INSERT INTO ZASSET VALUES (1, 10, 'IMG_0001.PNG', 'DCIM', ?, 0, 0, 7)",
            (cocoa(2024, 3, 3),),
        )
        connection.execute("INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (7, 42)")
        connection.commit()
        connection.close()
        payload = photos.read_bytes()
        photo_id = self._member("CameraRollDomain", "Media/PhotoData/Photos.sqlite", payload)

        cache_blob = plistlib.dumps({"Size": 5000, "LastModified": 1}, fmt=plistlib.FMT_BINARY)
        photo_blob = plistlib.dumps({"Size": 9000}, fmt=plistlib.FMT_BINARY)
        unknown_blob = b"not-a-plist"
        manifest = sqlite3.connect(self.backup / "Manifest.db")
        manifest.execute(
            """
            CREATE TABLE Files (
                fileID TEXT PRIMARY KEY,
                domain TEXT,
                relativePath TEXT,
                flags INTEGER,
                file BLOB
            )
            """
        )
        manifest.execute(
            "INSERT INTO Files VALUES (?, ?, ?, 1, ?)",
            (photo_id, "CameraRollDomain", "Media/PhotoData/Photos.sqlite", photo_blob),
        )
        cache_id = file_id_for("AppDomain-com.example.maps", "Library/Caches/tiles.bin")
        manifest.execute(
            "INSERT INTO Files VALUES (?, ?, ?, 1, ?)",
            (cache_id, "AppDomain-com.example.maps", "Library/Caches/tiles.bin", cache_blob),
        )
        manifest.execute(
            "INSERT INTO Files VALUES (?, ?, ?, 1, ?)",
            ("a" * 40, "HomeDomain", "Library/Notes/note.txt", unknown_blob),
        )
        manifest.commit()
        manifest.close()
        before = (self.backup / photo_id[:2] / photo_id).read_bytes()

        opened = open_backup(self.backup)
        summary = summarize_backup(opened)
        self.assertEqual(summary["device"]["device_name"], "Taylor's iPhone")
        self.assertNotIn("SECRET-SERIAL", json.dumps(summary))
        self.assertIsNone(summary["total_bytes"])
        self.assertEqual(summary["sized_bytes"], 14000)
        self.assertEqual(summary["cache_candidate_bytes"], 5000)
        domains = {row["domain"]: row for row in summary["domains"]}
        self.assertEqual(domains["AppDomain-com.example.maps"]["display_name"], "Example Maps")
        self.assertTrue(summary["largest_files"][0]["size_bytes"] >= summary["largest_files"][-1]["size_bytes"])

        work = self.root / "work"
        copied = copy_member(opened.root, photo_id, work / "Photos.sqlite")
        self.assertEqual((self.backup / photo_id[:2] / photo_id).read_bytes(), before)
        self.assertEqual(copied.read_bytes(), payload)
        with self.assertRaises(SafetyError):
            resolve_backup_member(opened.root, "../" + "a" * 40)
        with self.assertRaises(SafetyError):
            copy_member(opened.root, photo_id, opened.root / "evil.sqlite")

        completed = subprocess.run(
            [
                PYTHON,
                str(SCRIPTS / "screenshots.py"),
                "--backup",
                str(self.backup),
                "--out",
                str(self.root / "screenshots.csv"),
                "--work-dir",
                str(self.root / "work-copy"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Nothing was deleted.", completed.stdout)
        text = (self.root / "screenshots.csv").read_text(encoding="utf-8")
        self.assertIn("IMG_0001.PNG", text)
        self.assertEqual((self.backup / photo_id[:2] / photo_id).read_bytes(), before)

    def test_cache_and_plist_size_helpers(self):
        blob = plistlib.dumps({"Size": 42}, fmt=plistlib.FMT_BINARY)
        self.assertEqual(extract_size(blob), 42)
        self.assertIsNone(extract_size(b"nope"))
        self.assertTrue(is_cache_path("Library/Caches/x"))
        self.assertTrue(is_cache_path("Library/SplashBoard/snap"))
        self.assertFalse(is_cache_path("Library/Preferences/x.plist"))


class MvtAndReportTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_detections_and_empty_output(self):
        mvt_dir = self.root / "mvt"
        mvt_dir.mkdir()
        (mvt_dir / "configuration_profiles_detected.json").write_text(
            json.dumps(
                [
                    {
                        "matched_indicators": [
                            {"type": "configuration-profile:id", "value": "com.example.bad", "name": "Example"}
                        ]
                    }
                ]
            ),
            encoding="utf-8",
        )
        (mvt_dir / "sms_detected.json").write_text("[]", encoding="utf-8")
        (mvt_dir / "broken.json").write_text("{", encoding="utf-8")
        summary = summarize_mvt_output(mvt_dir)
        self.assertFalse(summary["proves_device_clean"])
        self.assertEqual(summary["detection_count"], 1)
        self.assertEqual(summary["detections"][0]["value"], "com.example.bad")
        self.assertIn("sms", summary["modules_with_detection_files_and_no_hits"])
        self.assertTrue(any("does not mean the iPhone is clean" in note for note in summary["notes"]))

        empty_dir = self.root / "empty"
        empty_dir.mkdir()
        empty = summarize_mvt_output(empty_dir)
        self.assertIsNone(empty["detection_count"])
        self.assertFalse(empty["proves_device_clean"])

    def test_report_is_bluf_and_preserves_notes(self):
        out = self.root / "out"
        out.mkdir()
        (out / "spyware_summary.json").write_text(
            json.dumps(
                {
                    "detection_count": 0,
                    "detections": [],
                    "modules_with_detection_files_and_no_hits": [],
                    "proves_device_clean": False,
                    "notes": ["No indicator match does not mean the iPhone is clean. [unverified]"],
                }
            ),
            encoding="utf-8",
        )
        (out / "deleted_photos.json").write_text(
            json.dumps(
                {
                    "asset_table": "ZASSET",
                    "counts": {
                        "assets": 3,
                        "recently_deleted": None,
                        "hidden": 1,
                        "hidden_and_recently_deleted": None,
                    },
                    "recently_deleted_bytes": None,
                    "hidden_bytes": 10,
                    "cloud_columns": {},
                    "notes": ["missing column [unverified]"],
                }
            ),
            encoding="utf-8",
        )
        report_path = self.root / "reports" / "iphone-cleanup-bluf.md"
        report_path.parent.mkdir()
        report_path.write_text(
            "old\n" + NOTES_BEGIN + "\nTaylor said the VPN is his.\n" + NOTES_END + "\n",
            encoding="utf-8",
        )
        text = build_report(out_dir=out, destination=report_path, generated_at="2026-11-02 00:00 UTC")
        self.assertTrue(text.startswith("# iPhone cleanup"))
        self.assertIn("Nothing was deleted.", text)
        self.assertIn("not available [unverified]", text)
        self.assertIn("does not show the iPhone is clean", text)
        self.assertIn("Taylor said the VPN is his.", text)
        self.assertNotIn("SECRET-SERIAL", text)
        self.assertLess(text.index("## Bottom line"), text.index("## Spyware"))


class PolicyTests(unittest.TestCase):
    def test_parsers_do_not_delete_or_ask_for_passwords(self):
        banned = (
            "os.remove",
            "os.unlink",
            "shutil.rmtree",
            ".unlink(",
            "rmtree",
            "getpass",
            "BACKUP_PASSWORD",
            "--password",
            "idevicebackup2 restore",
            "checkra1n",
            "palera1n",
        )
        sources = list((SCRIPTS / "iphone_cleanup").rglob("*.py"))
        sources.extend(SCRIPTS.glob("*.py"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        for snippet in banned:
            self.assertNotIn(snippet, text, snippet)

    def test_checklist_covers_the_required_settings(self):
        joined = json.dumps(ITEMS)
        for phrase in (
            "VPN & Device Management",
            "Safety Check",
            "Lockdown Mode",
            "iOS Version",
            "Photos",
            "device list",
        ):
            self.assertIn(phrase, joined)

    def test_gitignore_and_permissions(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for line in ("data/raw/*", "backups/", "reports/*"):
            self.assertIn(line, gitignore)
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        denied = "\n".join(settings["permissions"]["deny"])
        self.assertIn("rm -rf ~", denied)
        self.assertIn("rm -rf /Users", denied)
        self.assertIn("scp ", denied)
        self.assertIn("rsync ", denied)
        self.assertIn("curl ", denied)
        self.assertIn("idevicebackup2 restore", denied)
        self.assertIn("BACKUP_PASSWORD", denied)
        self.assertFalse(settings["sandbox"]["autoAllowBashIfSandboxed"])
        commands = ROOT / ".claude" / "commands"
        expected = {
            "setup.md",
            "backup.md",
            "spyware-scan.md",
            "device-checklist.md",
            "screenshots.md",
            "deleted-photos.md",
            "storage.md",
            "report.md",
        }
        self.assertEqual(expected, {path.name for path in commands.glob("*.md")})
        for path in commands.glob("*.md"):
            self.assertIn("Do not delete anything.", path.read_text(encoding="utf-8"))
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for phrase in (
            "explicit approval",
            "read-only",
            "jailbreak",
            "exfil",
            "[unverified]",
            "BLUF",
            "BACKUP_PASSWORD",
        ):
            self.assertIn(phrase, claude)


if __name__ == "__main__":
    unittest.main()
