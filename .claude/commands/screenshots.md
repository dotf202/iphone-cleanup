---
description: List screenshot candidates for Taylor's approval
allowed-tools: Bash(python3 scripts/screenshots.py *), Bash(.venv/bin/python scripts/screenshots.py *), Read
---

Build a list of screenshot candidates. Do not delete anything.

Use `$ARGUMENTS` as a backup folder, a `Photos.sqlite` path, or an export folder when Taylor passed one.

From a backup or database:

`python3 scripts/screenshots.py --backup <backup-folder>`

or, if he already copied the database out:

`python3 scripts/screenshots.py --photos-sqlite <path>`

From a Photos export folder (files he exported himself):

`python3 scripts/screenshots.py --export-dir <folder>`

The CSV is `data/out/screenshots.csv`. If the backup is still encrypted, follow the decrypt instruction the script prints. Let mvt prompt. Do not put the password on the command line or save it.

Reply with a short BLUF, not the whole CSV:

- counts by `asset_class` (screenshot, screen_recording, conflicting, export_file)
- UTC date range of the screenshot rows
- total size when the script has it
- the CSV path

Say that classification from `Photos.sqlite` follows public schema conventions (`ZKINDSUBTYPE` 10 for screenshots, 103 for screen recordings, a Screenshots album, or a Screenshot filename) and is `[unverified]` until he checks a sample on the phone. Rows already in Recently Deleted have `trashed_state` 1. An export folder lists every exported file, which is also `[unverified]` as a classification.

Stop there. Do not give deletion steps yet.

Give deletion steps only after Taylor explicitly approves this exact CSV in a later message that names `data/out/screenshots.csv` and says to delete those screenshots. Approval of a different file, or an earlier session, does not count. Even then, you still do not delete anything. He deletes on the phone:

1. Open Photos > Albums > Screenshots > Select.
2. Compare the count and the date range with the CSV. If they disagree, stop. The backup can be older than the phone.
3. If they match what he approved, he taps Delete. The items move to Recently Deleted for the period the album shows. They are not gone yet.
4. Permanent removal is a separate approval under `/deleted-photos`.

On-phone steps are the default. A Shortcut is optional, and only after the same approval. He builds it himself in the Shortcuts app. Action names can differ by iOS version; if a name is not there, he uses the Photos steps above. `[unverified]`

- Review shortcut: Find Photos where Album is Screenshots, then Quick Look. This one does not delete.
- Delete shortcut, only if he still wants it: Find Photos where Album is Screenshots, then Delete Photos.
  Warn him that it deletes the whole Screenshots album as it exists now, which can include shots taken after the backup. Prefer selecting by hand when the lists might differ.

Do not run the `shortcuts` command. Do not drive the Photos app. Screen-recording rows, conflicting rows, and plain export files are not part of the screenshot approval.
Do not delete anything.
