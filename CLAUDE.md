# Claude Code rules for Taylor's iPhone cleanup

This project runs on Taylor DeCelle's own Mac, in Claude Code, with his iPhone connected by USB. The job is local and defensive: look for spyware indicators, list leftover screenshots, report photos that were deleted but are still cached, and point at storage he can reclaim.

You read backups and write reports. Taylor decides what, if anything, is removed, and he removes it on the phone.

## Hard rules

1. **No deletion without explicit approval of a list.** Never delete a photo, app, profile, message, backup file, or cache entry on your own. Approval means Taylor's own message names the action and the exact file or item (for example: approve deleting the screenshots listed in `data/out/screenshots.csv`). Silence, "looks fine", a different file, or an older session does not carry over. After that approval you still do not delete. You give him the on-phone steps, and he taps them.
2. **Backups are read-only.** Analyze a backup. Do not modify files inside it. Do not restore it, unpack it with `unback`, turn encryption off, or change the backup password. Parsing copies go under `data/raw/` or `data/out/`.
3. **No jailbreak and no iOS security bypass.** Do not jailbreak the phone, install an exploit, mount a developer disk to get around the lock, or guess the passcode. If the phone is locked, ask Taylor to unlock it and tap Trust. If a step would need a jailbreak, stop and say so.
4. **No exfiltration.** Backups, decrypted copies, CSVs, MVT JSON, and reports stay on this Mac. Do not upload them, email them, AirDrop them, paste them into a third-party chat, or commit them. `MVT_NETWORK_ACCESS_ALLOWED=false` during `check-backup`, so URLs from the phone are not looked up on the network. Downloading public IOC feeds and the tools themselves is allowed. Do not send phone contents out to do it.
5. **Flag anything unverified.** If the backup does not prove a claim, mark it `[unverified]`. That includes schema guesses, a missing column, iCloud state, "no IOC match", and a backup that may be older than the phone. A missing count is "not available". It is not zero.
6. **BLUF.** Reports and chat answers lead with the bottom line: what you found, what you did not do, and that nothing was deleted.

## Passwords

Taylor types the backup password himself, into Finder's dialog or into a tool's own hidden prompt.

- Do not ask him to paste the password into the chat.
- Do not pass it as a command argument. Do not use a `--password` or `-p` flag.
- Do not set `BACKUP_PASSWORD` or `BACKUP_PASSWORD_NEW`.
- Do not write it into a file, a log, a report, the shell history, or this conversation.
- If a tool will only accept the password on the command line, stop and use Finder.

## What the commands are for

| Command | Result |
| --- | --- |
| `/setup` | Local venv, `mvt`, `libimobiledevice`, unit tests |
| `/backup` | Encrypted Finder or `idevicebackup2` backup over USB |
| `/spyware-scan` | `mvt-ios check-backup` with public STIX IOCs, then a summary |
| `/device-checklist` | Settings review he performs; you only record his answers |
| `/screenshots` | `data/out/screenshots.csv`, then wait |
| `/deleted-photos` | Recently Deleted and hidden counts, plus the steps to empty them |
| `/storage` | Largest domains, files, and cache-like paths |
| `/report` | `reports/iphone-cleanup-bluf.md` |

Run the Python scripts for numbers. Do not recompute them in your head and do not hand-edit them.

## Out of scope

- Cleaning the phone by restoring it, erasing it, or editing `Photos.sqlite`.
- Third-party "cleaner" apps.
- Enabling or disabling Lockdown Mode, Safety Check Emergency Reset, or iCloud Photos unless Taylor decides and does it himself.
- Any device that is not Taylor's, and any copy of this data that would leave the Mac.
