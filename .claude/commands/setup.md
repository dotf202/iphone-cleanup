---
description: Install the local venv, mvt, and libimobiledevice
allowed-tools: Bash(python3 -m venv *), Bash(python3 -m pip *), Bash(.venv/bin/pip *), Bash(python3 -m unittest *), Bash(brew install libimobiledevice *), Bash(brew list *), Bash(brew --prefix *), Bash(which *), Read
---

Set up this project on Taylor's Mac. Do not delete anything.

1. From the repo root, create `.venv` with `python3 -m venv .venv` if it is missing.
2. Install parser and scan dependencies with `.venv/bin/pip install -r scripts/requirements.txt`.
   That installs Amnesty International's Mobile Verification Toolkit (`mvt`) into the venv.
   The backup parsers themselves use only the Python standard library.
3. Run `python3 -m unittest discover -s tests -v`. The tests use synthetic databases.
   If they fail, stop and fix the project before touching a phone.
4. Check for `idevice_id`, `ideviceinfo`, and `idevicebackup2`.
   If they are missing, and Homebrew is already installed, run `brew install libimobiledevice ideviceinstaller`.
   If Homebrew is missing, stop and tell Taylor to install it. Do not download or pipe an install script.
5. Confirm `.venv/bin/mvt-ios` (or `.venv/bin/mvt`) responds to `--help`.
   Also try `mvt-ios download-iocs --help` and, if that subcommand is absent, `mvt download-iocs --help`.
   Remember which binary has `download-iocs`, `check-backup`, and `decrypt-backup`.

Do not plug the phone in during setup. Do not create a backup yet.
Do not delete anything.
