---
description: Report Recently Deleted and hidden photos, then the empty steps
allowed-tools: Bash(python3 scripts/deleted_photos.py *), Bash(.venv/bin/python scripts/deleted_photos.py *), Read
---

Report photos that were deleted but may still be stored. Do not delete anything.

`python3 scripts/deleted_photos.py --backup <backup-folder>`

or `--photos-sqlite <path>`. The JSON is `data/out/deleted_photos.json`.

If a count is `not available`, say that. Do not turn a missing column into zero.
Recently Deleted means `ZTRASHEDSTATE = 1` in this database. Hidden means `ZHIDDEN = 1`.
iCloud column numbers are counted and not interpreted. Mark them `[unverified]`.

Reply BLUF-style with:

- asset count, Recently Deleted count and size, hidden count and size
- date range of Recently Deleted when present
- the explicit limit: this file cannot prove an iCloud copy, a Shared Album, a Messages attachment, or another device is clear

Then give Taylor the steps. He performs them, and only after he explicitly approves emptying Recently Deleted. Approval to delete screenshots is not approval to empty Recently Deleted.

1. Photos > Albums > Recently Deleted. Read the countdown on the screen. Apple has historically kept items for about 30 days; the timer on his phone is the one that matters. `[unverified]` until he reads it.
2. Review the items. To remove them now: Select > Select All > Delete, or Delete All when that button is shown. This is permanent.
3. Hidden is separate. Photos > Hidden. Do not treat it as deleted. He reviews it and decides.
4. iCloud Photos, if enabled at Settings > [his name] > iCloud > Photos, syncs this delete, including the iCloud copy of those Recently Deleted items, after they are removed.
5. If iCloud Photos is off, emptying Recently Deleted is local. Copies can still exist from an earlier iCloud library, on another device signed into the Apple ID, in Shared Albums, or in Messages. He checks those himself.
6. Optimize iPhone Storage (the same Photos screen) keeps full copies in iCloud and smaller files on the phone. It does not empty Recently Deleted. Download and Keep Originals does the opposite. He opts in. It is a storage choice, not evidence that a copy is gone.
7. Leftover thumbnails are managed by Photos. There is no supported "clear thumbnail cache" switch. Do not delete `Photos.sqlite`, `Media/PhotoData`, or thumbnail folders by hand. That can corrupt the library, and this project does not restore a modified backup.

A local backup never proves the iCloud copies are gone. Keep that sentence `[unverified]` no matter what the JSON says.
Do not delete anything.
