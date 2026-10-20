# OMORI Translation Installer

Canonical project: `/Users/antonkrutov/Desktop/omori full translation mod`.
The macOS app targets the native macOS game. The Windows app targets the Windows
game; CrossOver is a Windows-development/test environment only. Steam application
ID is **1150690**. **8879120** is the supported game content build, not its app ID.

## Player flow

Close OMORI, open the application, select a language and install. The app discovers
Steam libraries; choose the game folder if necessary. After success, launch through
Steam. Reopen the app to switch languages while the game is closed. All included
languages are installed in isolated compressed package storage; one locale is active.
No translator, model account, developer tools or API key is required by players.

The adapter uses the native EN resource channel. Each locale includes overlapping
native data, scripts, fonts and EN catalogs, so unpacking all locale ZIPs into one game
folder is unsafe. Selection belongs in the installer for this adapter.

## Base and changes

Adapted from read-only `/Users/antonkrutov/Desktop/StardewTranslationInstaller`,
inspected at `013686ba518c9e11140544a05443dc6ad4fadbdd`. That base was not modified.
Reuse: SwiftUI shell/AppState flow, native Windows controls/worker/status interface,
Steam-library discovery, folder fallback, hash/staging/ownership protection and
universal macOS/native Windows packaging patterns.
OMORI-specific: folder markers, Steam ID, branding, language selector, exact native
payload restoration, per-file original backup and multi-file recovery journal.
SMAPI, Content Patcher and Stardew language-switcher dependencies do not apply.

The Windows UI uses a native C++ game adapter rather than the base PowerShell
helper. CrossOver's bundled PowerShell executable returned success without executing
an actual file-write probe. The native adapter avoids an extra engine/dependency and
keeps the original UI/worker contract. It uses Windows BCrypt and statically linked
zlib; no runtime download is required. Vendor pins/licenses are in `vendor/PROVENANCE.json`.

## Packaging

`Scripts/prepare_payload.py` consumes already verified locale ZIPs, checks their exact
file sets/hashes, decrypts native resources for compression, and verifies that encoding
with each original IV reproduces the delivered ciphertext. Fonts/raw files remain exact.
Objects are deduplicated by plaintext SHA256 and gzip-compressed. No wording is generated
and no native compilation/editorial review is rerun. The catalog records each locale's
actual source ZIP hash and review state; technical candidates are not editorial acceptance.
The app and native Windows helper reconstruct and hash every selected output before writes.

```
python3 -B installer/Scripts/prepare_payload.py --output build/installer/NEW_PAYLOAD
installer/Scripts/build-mac.sh build/installer/NEW_PAYLOAD
installer/Scripts/build-windows.sh build/installer/NEW_PAYLOAD
```

`--reuse build/installer/COMPLETED_PAYLOAD` verifies and reuses immutable compressed objects instead of recompressing unchanged translations. Font license text is exported separately. Owner-paused locales keep their verified packaged checkpoint available to the installer.

`--allow-pending` is for explicitly incomplete development builds only. Preserve
existing release artifacts and use a fresh revision. Build scripts reject incomplete payloads before compilation and preserve existing
app/stage/archive paths. Set `OMORI_RELEASE_DIR` to a fresh revision for both platforms. macOS requires Command Line Tools/Swift; Windows cross-build requires
Homebrew MinGW-w64 and the pinned static zlib build. Players need neither.

For a payload-only update, `Scripts/repack_verified_mac.py` reuses the immutable
universal app core pinned by `installer-finalize-r3-snapshot/manifest.json`, the
same boundary used by the existing finalizer. It verifies both seed hashes,
both architectures, the complete payload object hashes, ad hoc signing, and
every ZIP entry against the staged app. Existing outputs are preserved. This
avoids recompiling unchanged installer code when only locale resources change.
The October 19 release uses this path after the current Swift Build backend
failed to emit an Intel dependency file. The resource-only packaging boundary
is recorded in the release receipts. Repacking does not establish a new
real-game runtime test.

## Storage and recovery

The game resource root contains `.vnrevival-omori` with an exclusive install lock,
content-addressed immutable backup blobs, compressed full-set packages, `state.json`
and (only during installation/recovery) `journal.json`. Never remove this directory
while a translation is installed. Unknown modifications, unsafe paths, links and
unsupported originals stop the operation without overwriting those files.

Before the first asset write, all planned before/after bytes are staged and hashed,
and the durable journal records the previous install state. Each file replacement is
atomic; the whole directory is not a filesystem transaction. On interruption, the next
invocation first validates every affected current file against its before/after hash,
restores the complete previous state, then proceeds with the requested selection.
Unknown changes after interruption block recovery and remain untouched. A failure after
state.json but before journal removal also restores the previous state. Saves and official
non-EN packs are outside the allowed resource paths. Original EN resources are backed
up before intentional replacement and restored for old-only paths on locale changes.

## Validation boundaries

Tests use disposable game folders and exercise actual file IO, gzip, native AES-CTR,
hashes, locale persistence, switching, interruption and conflict handling. They do not
establish game rendering, font shaping, dialogue correctness or route coverage. Keep
native macOS, CrossOver, native Windows, signing/notarization and editorial acceptance
separate in the final artifact receipt. A passing CrossOver test is not a native Windows
runtime test. No game save is created or overwritten by installer tests.

## Windows resource-root regression

The Steam Windows build has an outer `package.json` with `main: www/index.html`
and duplicate `data/System.KEL` outside `www`. Discovery follows the actual NW.js
entry point: only a resource folder with `main: index.html`, that entry file and
System.KEL is eligible. Selecting the game folder and selecting its persisted
`www` folder resolve to the same resource root. Fixture checks include duplicate
outer data and an outer index file, plus a direct-root positive control.

## October17 resumed build

The owner resumed both native app builds and authorized real Windows testing in
CrossOver after installing OMORI build8879120. The Hebrew CLI lane remains active;
batch editorial review remains deferred. Payload-v4 reuses the unchanged completed
v2 catalog and all 6,774 compressed objects and adds six readable font licenses.
It currently contains Russian plus25 packaged target locales; Hebrew remains pending.
Previous incomplete build folders and earlier ZIPs remain preserved.

## Final full-set assembly

The owner confirmed native Mac OMORI runs in Russian on October17. This exercised
the pre-existing byte-verified Russian overlay and main menu; the new Mac installer
was opened read-only and was not applied over that existing mod. Windows installation,
French switching and persisted selection passed in CrossOver, then the owner paused
Windows testing before game rendering was accepted.

`Scripts/finalize_after_hebrew.py` waits for Hebrew's actual packaged checkpoint,
then uses its immutable helper/binary snapshot to create `dist/installer/1.0.0-r3/`
with Russian and all26 target locales. It preserves prior builds and verifies every
ZIP entry against the packaged stage. `prepare_payload.py --root PROJECT` allows a
frozen helper to read canonical project inputs. No live source helper is loaded later
from the checkout. The finalizer uses no LLM, never launches a game or CrossOver,
and reports waiting, building, complete or needs-attention to the saved status file.
Its current process/lock identity must be reconciled before any retry.

## Site archive language metadata

All packaging entry points call `Scripts/write_site_locale_manifest.py` before
signing or archiving. The site manifest declares the shared catalog, compressed
object directory and a separate inventory for each of the 27 locales. Each
inventory contains the exact locale file records and catalog fingerprint;
manifest inventory hashes bind those records to this package. The producer
verifies every referenced gzip object's packed hash, size and decompressed hash
before writing metadata. The site audit proves structural presence; the local
producer and archive readback establish complete object coverage. Repacking
metadata does not replace gameplay QA or editorial acceptance.

## Rebuilding after local cleanup

The exact published source payload is `source/release-payload-1.0.0`. Use a fresh
release directory; existing distributions are preserved:

```sh
OMORI_RELEASE_DIR="$PWD/dist/installer/NEW_REVISION" installer/Scripts/build-windows.sh source/release-payload-1.0.0
python3 installer/Scripts/repack_verified_mac.py --seed dist/installer/1.0.0-site-20261019-02/build-seed --payload source/release-payload-1.0.0 --release dist/installer/NEW_REVISION
```

The Windows script recreates its build directory and pinned zlib static library
from the retained vendor sources. Mac source compilation remains available via
`build-mac.sh`; the resource-only repacker retains its existing tested-core boundary.
The old QA catalogs referenced by historical final-input records were temporary
inputs and were removed. Those records remain provenance, while the retained
release payload is the current direct packaging input. Do not rerun the historical
assembler against missing paths. Source data and binaries remain private local
inputs unless separately authorized for publication.

## Native launch verification

Launch OMORI through Steam, then confirm that its native process is already
running with Steam's required launch argument before attaching a UI inspector.
Some inspection APIs automatically launch an absent app without arguments,
which can produce a black window before the encrypted plugins load. Do not
interpret that window as a translation failure. Regression: start from a closed
game, launch through Steam, verify the process first, and then confirm the
selected language in the rendered main menu. Never print the launch argument.

## Exact-source macOS provenance

For a new macOS archive, use `Scripts/build-provenance.py --platform macos`
with the retained payload and a fresh release directory. The recipe compiles both
architectures from the recorded clean, pushed commit, verifies the universal
binary and ad hoc signature, and compares every ZIP file with the staged app.
The macOS script explicitly selects SwiftPM's native build backend: the default
Swift Build backend in Swift 6.4 previously failed to emit an Intel dependency
file. Existing resource-only repacks retain their original provenance boundary.
This build does not claim Apple notarization or a new gameplay acceptance run.
