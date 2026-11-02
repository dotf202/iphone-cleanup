---
description: Make an encrypted local USB backup without storing the password
allowed-tools: Bash(idevice_id *), Bash(ideviceinfo *), Bash(idevicebackup2 -i encryption on), Bash(idevicebackup2 backup --full *), Bash(idevicebackup2 info *), Read
---

Create an encrypted backup of Taylor's iPhone. The phone is connected by USB to this Mac.
Do not delete anything.

Prefer Finder, so the password is typed into Apple's dialog and never enters the chat:

1. Ask Taylor to unlock the iPhone, connect a USB cable, and tap Trust if prompted.
2. Tell him to open Finder, select the iPhone in the sidebar, and under General > Backups choose **Encrypt local backup**.
3. He types the backup password in that dialog himself. Do not ask him to paste it here.
   Tell him to remember it: it is required for a future restore, and this project will not store a copy.
4. He clicks **Back Up Now** and waits until Finder finishes.
5. The folder is `~/Library/Application Support/MobileSync/Backup/<UDID>/`.
   Ask for that folder path. Do not ask for the password. Do not read the macOS keychain.
6. Confirm `Manifest.plist` exists. Later commands check whether it is encrypted.

Use the command line only when Finder cannot see the phone. USB only. Do not pass `-n` (that is a network backup).

1. `idevice_id -l` should print a UDID. If it does not, stop at the cable, unlock, and Trust prompt.
2. Turn on encryption with an interactive prompt and no password argument:
   `idevicebackup2 -i encryption on`
   Taylor types the password at that prompt. If the tool instead requires the password as an argument, stop and use Finder.
3. Write the backup only under the gitignored folder:
   `idevicebackup2 backup --full data/raw/backup`
4. Do not set `BACKUP_PASSWORD` or `BACKUP_PASSWORD_NEW`. Do not echo the password. Do not put it in a file, a report, or the chat.

Never run restore, `encryption off`, `changepw`, `cloud`, or `unback`.
Do not delete anything.
