---
description: Walk Taylor through the on-phone Settings checks
allowed-tools: Bash(python3 scripts/device_checklist.py *), Bash(.venv/bin/python scripts/device_checklist.py *), Read
---

Walk Taylor through a manual Settings review. The phone stays in his hands.
Do not delete anything. Do not change a setting yourself. Do not run Shortcuts, AppleScript, or a restore.

Start by printing the current list:

`python3 scripts/device_checklist.py`

Cover these items, in this order, and wait for Taylor's answer before recording one. If he has not looked yet, leave the status `not_checked`.

1. **Configuration profiles, VPN, and device management.** Settings > General > VPN & Device Management.
   Anything he does not recognize is `needs_attention`. Do not remove a profile unless he later says to do that himself, and this command does not remove it.
2. **Apple ID devices.** Settings > his name at the top > the device list at the bottom.
   An unknown device is a lead, not proof of spyware. He can remove a device there. You cannot.
3. **Safety Check.** Settings > Privacy & Security > Safety Check.
   Use the review only. Do not recommend Emergency Reset unless he explicitly asks for that broader reset.
4. **App permissions.** Settings > Privacy & Security, then Location Services, Photos, Camera, Microphone, Bluetooth, Local Network, and Contacts.
   Note apps he does not remember allowing, especially Photos set to Full Access, Microphone, Camera, and Location set to Always. Do not toggle them.
5. **Unknown apps.** Home screen and Settings > General > iPhone Storage.
   Write down names he does not recognize. Do not delete an app.
6. **iOS version.** Settings > General > About > iOS Version. Record the version he reads.
   You may look up Apple's public security-update page to compare. Until that comparison is done, mark the comparison `[unverified]`.
   He installs updates himself in Settings > General > Software Update.
7. **Lockdown Mode.** Settings > Privacy & Security > Lockdown Mode.
   It is optional protection for someone who may be personally targeted by sophisticated spyware.
   It restricts some attachments, FaceTime calls from unknown callers, wired accessories while the phone is locked, configuration profiles, and some web technologies. Some sites and features break.
   Leave the switch where he found it unless he decides to change it. He is the one who toggles it.

Record an answer only after he gives it:

`python3 scripts/device_checklist.py --set <id>=<not_checked|looks_ok|needs_attention|unverified> --note <id>="what Taylor said"`

Do not invent a status. Do not pass `--reset` unless he asks to clear the checklist.
Do not delete anything.
