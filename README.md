# iPhone cleanup

Local checkup for Taylor DeCelle's iPhone. Claude Code runs on his Mac. The phone is plugged in over USB. The work stays on that Mac.

Three jobs:

1. Look for spyware indicators in an encrypted backup, using Amnesty International's [Mobile Verification Toolkit](https://github.com/mvt-project/mvt) and its public IOC feeds.
2. List leftover screenshots so Taylor can approve a list before anything is removed.
3. Report photos that were deleted but are still in Recently Deleted, hidden, or possibly still in iCloud, and report what is using storage.

Nothing is deleted unless Taylor approves a specific list and then deletes it himself on the phone. The backup is read-only. The phone is not jailbroken. Reports say when a finding is unverified, and they lead with the result.

## Open the project

On the Mac, in this repo:

```bash
claude
```

Then:

1. `/setup` — Python venv, `mvt`, and `libimobiledevice`. Also runs the unit tests.
2. `/backup` — encrypted local backup. Taylor types the backup password into Finder. It is not saved here.
3. `/spyware-scan`
4. `/device-checklist`
5. `/screenshots` — writes `data/out/screenshots.csv` and waits.
6. `/deleted-photos`
7. `/storage`
8. `/report` — writes `reports/iphone-cleanup-bluf.md`.

`TASK.md` is the session order. `CLAUDE.md` is the rule set Claude Code has to follow. `docs/PLAN.md` explains why the backup is analyzed this way.

## What you will see

| Path | What it is |
| --- | --- |
| `.claude/commands/` | The slash commands above |
| `.claude/settings.json` | Denies `rm -rf` of the home directory, denies upload tools, keeps backup and jailbreak commands off |
| `scripts/` | Standard-library parsers for Photos.sqlite, backup sizes, and MVT JSON |
| `data/raw/` | Backup and decrypted copy. Gitignored. |
| `data/out/` | CSV and JSON results. Gitignored. |
| `reports/` | The BLUF report. Gitignored except this folder's template. |

Parsers do not need a phone to test:

```bash
python3 -m unittest discover -s tests -v
```

## Safety, in short

- Taylor approves a named list before any deletion steps are even described, and he performs the taps.
- The backup password is typed into Finder or into the tool's own prompt. It is never put in the chat, a file, or `BACKUP_PASSWORD`.
- `mvt` is not allowed to phone home with URLs taken from the device during the check.
- A lack of IOC matches does not mean the phone is clean. A row in the screenshot CSV is a candidate until Taylor recognizes it. Recently Deleted in one backup does not prove iCloud has forgotten the photo.
