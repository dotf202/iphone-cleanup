---
description: Write the combined local BLUF report
allowed-tools: Bash(python3 scripts/build_report.py *), Bash(.venv/bin/python scripts/build_report.py *), Read
---

Write the combined report from the local output files. Do not delete anything.

`python3 scripts/build_report.py`

This writes `reports/iphone-cleanup-bluf.md` and a dated copy next to it. Both are gitignored.
The script fills the numbers. Do not retype or "correct" them by hand.
Sections that were not run stay "not run". A missing count stays unavailable. Do not invent a zero.

Read the report back to Taylor BLUF-style: the bottom line first, then the shortest version of each section.
Repeat that nothing was deleted.
Repeat any `[unverified]` limit the report includes, especially:

- no IOC match does not mean the phone is clean
- screenshot classification needs a sample confirmed on the phone
- Recently Deleted in the backup does not prove iCloud copies are gone
- cache-like paths are not a delete list

You may add a sentence inside the session-notes markers only when it is something Taylor said in this session. Do not put analysis there.

Do not commit the report. Do not upload it. Do not delete anything.
