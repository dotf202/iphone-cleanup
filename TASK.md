# Task: one cleanup session

Do these in order. Stop at each approval gate. Do not delete anything yourself.

1. `/setup` — venv, mvt, libimobiledevice, and `python3 -m unittest discover -s tests -v`.
2. `/backup` — encrypted local backup over USB. Taylor types the password. You store only the folder path.
3. `/spyware-scan` — public IOC feeds, then `check-backup` with network lookups off. Summarize matches. Do not call a miss a clean phone.
4. `/device-checklist` — he checks Settings. Record only what he tells you.
5. `/screenshots` — write `data/out/screenshots.csv`. Show the count, date range, size, and path. **Stop.**
6. Wait for explicit approval of that CSV before you describe how he deletes screenshots on the phone.
7. `/deleted-photos` — report Recently Deleted and hidden counts. **Stop.** Emptying Recently Deleted needs its own approval. Screenshot approval is not it.
8. `/storage` — largest apps and cache-like paths, plus Settings steps. Cache paths are not a delete list.
9. `/report` — combined BLUF in `reports/`. Do not commit or upload it.

## Done when

- The BLUF report is on this Mac and Taylor has seen it.
- Spyware, screenshots, deleted-photo counts, storage, and the checklist are each either filled from a real run or marked not run.
- Every uncertain claim is marked `[unverified]`.
- Nothing was deleted unless Taylor deleted it himself, on the phone, after approving the specific list.
- `data/raw/`, `data/out/`, `reports/iphone-cleanup-bluf.md`, and the backup folder are still untracked.

## Approval gate

An approval message from Taylor names both the action and the list:

- "Approve deleting the screenshots in `data/out/screenshots.csv`."
- "Approve emptying Recently Deleted, the count in `data/out/deleted_photos.json`."

After either message, give him the steps and stop. You still do not delete anything.
