---
description: Run mvt-ios against public IOCs and summarize matches
allowed-tools: Bash(.venv/bin/mvt-ios *), Bash(.venv/bin/mvt *), Bash(mvt-ios *), Bash(mvt *), Bash(python3 scripts/spyware_summary.py *), Bash(.venv/bin/python scripts/spyware_summary.py *), Read
---

Look for known spyware indicators in a local backup. Do not delete anything.

The backup path is `$ARGUMENTS` when Taylor passed one. Otherwise use the folder from `/backup`.

1. If `Manifest.db` is not readable SQLite, the backup is still encrypted.
   Decrypt a copy into `data/raw/decrypted`. Run `mvt-ios decrypt-backup --help` (or `mvt decrypt-backup --help`) and use the destination flag it documents.
   Let the tool prompt for the password. Never pass the password as an argument, an environment variable, or a file. Never write it down.
2. Download the latest public STIX indicators. Prefer `mvt-ios download-iocs`. If that subcommand is missing, use `mvt download-iocs`.
   This is a download of published feeds, not an upload of phone data.
   Record the directory it prints. If it does not print one, look in `~/Library/Application Support/mvt` and `~/.local/share/mvt`.
   If no indicator file is found, stop. Do not call the result a clean scan.
3. Run the check with network access off so URLs found on the phone are not resolved remotely:
   `MVT_NETWORK_ACCESS_ALLOWED=false .venv/bin/mvt-ios check-backup --output data/out/mvt <decrypted-backup>`
   Add `--iocs` for each downloaded `.stix2` or `.json` indicator file when `--help` shows that flag.
   Do not pass `--fast` unless Taylor asks. A fast run is a partial scan and must be labeled `[unverified]`.
4. Summarize only the local JSON:
   `python3 scripts/spyware_summary.py --mvt-dir data/out/mvt`
5. Reply BLUF-style:
   - how many indicator matches were parsed
   - the module, indicator name, and value for each match, up to 30, with the local JSON path for the rest
   - the IOC directory that was used
   - this sentence when the count is zero: the scan found no matches in the artifacts it could read, and that does not show the iPhone is clean
   - `proves_device_clean` is always false

Do not paste message bodies or contact lists into the chat. Do not upload `data/out/mvt`.
A match is a lead for Taylor to review, not proof. No match is not a clean bill of health. Mark both limits `[unverified]`.
Do not delete anything.
