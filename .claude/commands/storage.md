---
description: Report the largest apps and cache-like backup paths
allowed-tools: Bash(python3 scripts/storage_report.py *), Bash(.venv/bin/python scripts/storage_report.py *), Read
---

Report what is using space in the local backup. Do not delete anything.

`python3 scripts/storage_report.py --backup <backup-folder>`

Writes `data/out/storage_summary.json`, `data/out/storage_by_domain.csv`, and `data/out/storage_largest_files.csv`.

Reply BLUF-style:

- iOS version and device name when the summary includes them. Do not add serial number, IMEI, phone number, or UDID.
- sized total, and say the total is incomplete when the script does
- the largest domains, with display names when known
- the largest files
- cache-like bytes, labeled as leads `[unverified]`

Cache-like means a path such as `Library/Caches`, `tmp`, `SplashBoard`, or `Cache.db`. Those files can be recreated and can also hold sign-in state. They are not a delete list. Do not remove them from the backup or the phone by hand.

Optimization he can do himself in Settings > General > iPhone Storage, after he decides app by app:

- Offload Unused Apps removes the app but keeps its documents. Delete App removes the app and its data. He chooses. You do not.
- Review large message attachments from that same storage screen.
- Review offline downloads in Music, TV, and Podcasts.
- For photos, Optimize iPhone Storage is the supported control, described in `/deleted-photos`.
- System Data is not a safe manual delete target.
- Do not install a "cleaner" app.

Do not `rm` a cache path. Do not delete anything.
