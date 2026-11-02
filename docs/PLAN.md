# Plan

Taylor's iPhone stays in his hands. Claude Code, on his Mac, reads an encrypted local backup and writes lists. Deletion, if it happens, is a tap he makes in Photos or Settings after he has approved a specific list.

## Why a backup

A Finder or `idevicebackup2` backup is the supported way to read an iPhone without jailbreaking it and without changing it. The phone must be unlocked and trusted. The backup is encrypted so a copy of the library is not left in the clear on disk until Taylor chooses to decrypt a working copy for analysis.

That copy is still not the whole phone. An iOS backup omits some artifacts. It can be older than the phone by the time he looks at Photos. It does not prove what iCloud, another device on the same Apple ID, Shared Albums, or Messages still hold. Those limits are marked `[unverified]` in the report rather than papered over.

## Flow

1. `/setup` installs a project venv, Amnesty International's Mobile Verification Toolkit (`mvt`), and `libimobiledevice`. Unit tests use synthetic SQLite files and do not need a phone.
2. `/backup` prefers Finder's encrypt-local-backup dialog. The command-line fallback is `idevicebackup2 -i encryption on` with no password argument, then `idevicebackup2 backup --full` into `data/raw/backup`. USB only.
3. If `Manifest.db` is not SQLite, `mvt-ios decrypt-backup` prompts for the password and writes `data/raw/decrypted`. The password is not stored.
4. `/spyware-scan` downloads the public STIX feeds with `mvt-ios download-iocs` (or `mvt download-iocs` on builds where that subcommand moved). `check-backup` then runs with `MVT_NETWORK_ACCESS_ALLOWED=false`, so indicator URL shortening is not resolved by sending phone URLs onto the network. `scripts/spyware_summary.py` counts `matched_indicators` in the local JSON. Zero matches do not mean the phone is clean. The feeds are incomplete, and a match is a lead, not proof.
5. `/device-checklist` is a spoken pass through Settings: VPN and Device Management, the Apple ID device list, Safety Check, app permissions, unknown apps, the iOS version, and Lockdown Mode. The script records his answers. It does not toggle anything.
6. `/screenshots` reads `CameraRollDomain/Media/PhotoData/Photos.sqlite`, or a folder he exported from Photos. Rows are written to `data/out/screenshots.csv`.
7. `/deleted-photos` counts `ZTRASHEDSTATE = 1` and `ZHIDDEN = 1` and lists iCloud-related columns without interpreting the numbers.
8. `/storage` sums sizes from the `Size` field in each `Manifest.db` file plist, grouped by domain, and flags cache-like paths.
9. `/report` assembles `reports/iphone-cleanup-bluf.md` from those files. The bottom line is first. Session notes he dictated are kept across reruns. Numbers are not rewritten by hand.

## How a screenshot is recognized

The parser keeps a row when any of these is true:

- `ZISDETECTEDSCREENSHOT` is set
- `ZKINDSUBTYPE` is 10 (screenshot) or 103 (screen recording), the values used in public Photos.sqlite write-ups
- the asset sits in an album titled Screenshots or Screen Recordings
- the original filename looks like `Screenshot…` or `Screen Recording…`

An ordinary photo is not included just because it is a PNG. A file in an export folder is included because he exported it, with that reason in the CSV. All of these are conventions. The report says so, and Taylor confirms a sample on the phone before any deletion list is approved.

Dates in the database are Core Data timestamps (seconds since 2001-01-01 UTC) and are converted to UTC. File size prefers `ZORIGINALFILESIZE`. If that column is missing, the size is blank rather than guessed.

If `ZTRASHEDSTATE` or `ZHIDDEN` is absent, the count is null. The report says "not available". It does not say zero.

## What is deliberately not automated

- Deleting photos, emptying Recently Deleted, removing a profile, uninstalling an app, or turning on Lockdown Mode.
- Hand-deleting `Photos.sqlite` or thumbnail caches. Photos rebuilds its own thumbnails. Removing the database by hand can corrupt the library, and this project will not restore a backup it has edited.
- Reading the macOS keychain for the backup password.
- Uploading the backup to scan it elsewhere.

On-phone steps live in the slash commands. The screenshot steps compare the album on the phone with the CSV before he taps Delete, because the phone may have new shots. A Shortcut recipe is optional and is something he builds and runs himself. The `shortcuts` and `osascript` commands are denied so the agent cannot press Delete for him.

## Permissions

`.claude/settings.json` is the mechanical half of the rules in `CLAUDE.md`.

- Manual permission mode. Bypass mode and auto mode are disabled.
- `rm -rf` aimed at the home directory, `/Users`, or `/home` is denied, including a few flag variants. Any other `rm` still asks.
- Upload-shaped tools are denied: `curl`, `wget`, `scp`, `sftp`, `rsync`, `rclone`, `ssh`, netcat, cloud CLIs, `git push`, and forced git adds of `data/` and `reports/`.
- Device-destructive commands are denied: backup restore, encryption off, unback, changepw, firmware restore, recovery, diagnostics, and the common jailbreak tool names.
- `BACKUP_PASSWORD` is denied both as a command-line string and as a sandbox environment variable.
- The sandbox allows package and IOC hosts (PyPI, GitHub, Homebrew) and does not auto-approve sandboxed commands. `idevice*` is excluded from the sandbox because it has to reach the USB daemon; those commands still go through the permission prompt, and the destructive subcommands stay denied.
- The sandbox does not understand HTTP methods. An allowed host can still receive a request. The deny rules and the "no exfiltration" rule are what keep phone contents off the network. Permission patterns also do not see every absolute path or every child process. They are a backstop, not a substitute for the rules above.

Personal outputs are gitignored: `data/raw/`, `data/out/`, backup folders, SQLite files, backup plists, and generated reports. `reports/TEMPLATE.md` is the only report file that belongs in git.
