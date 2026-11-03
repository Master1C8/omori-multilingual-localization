# Source-only archival

The laptop retains canonical editable source and Git history, authored translations,
approved glossaries, runtime JS, editable fonts/licenses and editing instructions.
Player saves are protected separately. GitHub holds the existing accepted macOS and
Windows 1.0.0 installers and a checksummed maintainer-only minimal source/input draft.
See [recovery](Documentation/RECOVERY.md) for restore and normal build commands.

The public repository remains writable and its history/visibility are preserved.
No game, model queue, deployment or publication was started during archival.
Historical acceptance is retained; this audit does not claim a fresh gameplay test.

Final source-only cleanup completed on 2026-11-03. The fingerprinted administrator
helper ran through direct sudo in Terminal and removed the last obsolete runtime-check
tree (21 files,258,707 logical bytes). Its exact path was independently verified absent.
All 8,683 locally retained authored files were rehashed unchanged against the verified
private source capsule. The earlier cold restoration and both normal builds remain
applicable; only retired QA output and this documentation changed.

The laptop now retains canonical editable source and normal Git metadata, with
PreservedSaves protected separately. Generated payloads, installers, screenshots,
local build caches and installed environments are retired. Existing accepted GitHub
artifacts and the unpublished minimal private source/input draft remain unchanged.
