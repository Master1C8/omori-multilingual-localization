# Windows installer regression checks

Use the actual public archive in the existing Parallels Windows environment.
Preserve saves and establish the clean Steam baseline before applying it. The
release check ends at a reviewed localized main menu; the installer dialog alone
does not prove success.

## Execution level

Every executable, including `OmoriInstallHelper.exe` and this UI driver, must
embed an `asInvoker`, `uiAccess=false` manifest. Compile
`Windows/Installer.rc` with windres and link that resource object into both
delivered executables. Include the same resource when compiling `driver.cpp`.
Do not request administrator rights or change UAC settings to make a test pass.

Regression observed on Windows 11 ARM, build 26200: the original release's
unmanifested helper exists and matches the public ZIP hash, but a normal-user
`CreateProcessW` returns error 740. Its GUI reports that the helper could not
start. The public helper SHA-256 is
`40b7a45abd1422f160bf4b197e47a0c9e9f31820166ccffefaf0416093244f60`.

Use that exact original helper as the negative control. A rebuilt helper with
the embedded manifest must start through the same normal-user `CreateProcessW`
boundary. A no-argument probe is safe only after checking that the entry point
rejects `argc < 6` before accessing any game path; successful process creation
and its expected invalid-invocation exit are separate results. Then test the
complete packaged installer through its normal controls and the real game.

## Control and capture

Native Parallels key events and this Win32 UI driver are alternatives only when
the owner explicitly authorizes them. The driver verifies the running installer
executable before acting. Verify the selected locale against the actual archive's
`Resources/languages.tsv`; Hebrew is index 26 in the tested 27-language release.

After a launcher timeout, unexpected UAC prompt or contradictory exit status,
reconcile the receipt, process and actual window before retrying. In the original
test, Hebrew selection succeeded and wrote its JSON despite a PowerShell error.
Never infer that no action occurred from that error alone.

For an owner-authorized native window capture, verify the game executable, PID
and unique visible `OMORI` window. An unedited client capture with
`PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT)` was verified against the
English baseline; it excludes the desktop and Windows activation watermark.
Review the actual localized pixels again for each final result. Preserve the
raw PNG and capture receipt; do not crop away desktop contamination afterward.

## Final-archive acceptance evidence

Bind every run to the SHA-256 of the final downloaded or prepared ZIP, and
verify that the executed GUI/helper come from that extraction. An existing
localized installation tests upgrade/switching; separately establish original
resource hashes and no install state before claiming a clean installation.
Preserve the original locale, protected metadata and saves before either test.
Test interruption with the delivered helper, assert the intended failure message
and actual partially changed files, then verify exact previous-state recovery.
Restore the owner's original state and compare its owned files and saves.

A visible `OMORI` window is not a rendered-menu readiness marker. On Windows 11
ARM64 the October 20 final-archive test captured a black frame during startup
before the French menu appeared. Preserve that diagnostic frame, inspect actual
rendered state, and capture again only after the menu is present; do not credit
a blank image or a fixed 15-second delay as launch success. Keep x64-on-ARM
execution distinct from testing on native x64 hardware, and do not extrapolate
a main-menu check into full-gameplay acceptance.

When mixing GUI and direct-helper checks, read and reuse the exact `gameRoot`
from the current protected state (including casing). The current helper compares
this identity as a string, even on case-insensitive Windows. Do not substitute a
manually capitalized equivalent path or rewrite protected metadata to bypass
that guard. For a clean-baseline run, retain the previously resolved path before
preserving the metadata directory. Regression: the Steam-resolved lower-case
path and `C:\Program Files (x86)\Steam` name the same directory but a direct
helper run with the second spelling creates a different recorded identity;
the existing GUI correctly reports its identity mismatch before resource writes.
Record this path-spelling limitation separately from installation/recovery results.
