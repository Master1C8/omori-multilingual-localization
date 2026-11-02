# Editable source and build-input recovery

The public repository contains installer/tool source. Canonical authored batches,
drafts, approved glossaries, editing notes, runtime source and editable fonts remain
in the local source checkout. Their recovery copy and the current shared extraction
context are in an unpublished maintainer-only draft; repository visibility is unchanged.

`archival-sources.json` pins `OMORI-Source-Inputs-20261103.zip` in draft
`private-editable-inputs-2026-11-03` of `Master1C8/omori-multilingual-localization`.
The ZIP is 88,144,555 bytes, SHA-256
`8842bfc514832bb128361a079b7873818b6e919599512242bc817b9b161f1120`.
Its private `_SOURCE_MANIFEST.json` pins every file. The 13,051 files include
8,602 editable translation records, 48 glossary records, 4,368 shared-source
context files, four runtime JS sources, six editing notes and 23 editable fonts/license
files. Raw member contents total 344,217,680 bytes. Filenames/private editing data
are deliberately absent from this public locator.

From the canonical project root, authenticate as Master1C8 and restore:

```sh
python3 -B scripts/restore_private_sources.py
```

Restore a single group with `--group source-context` or `--group translations`.
`--rehearse .build/recovery-check` uses a separate generated validation directory
inside this project. The helper checks the archive, embedded inventory and every
selected file. Existing matching files remain unchanged; any edited/mismatching file
blocks publication before other files are written. Extra files are preserved.
Missing files are published exclusively and atomically per file; a later failure is
resumable, not a multi-file transaction. Never overwrite newer local edits to match
an older archive. Keep the draft unpublished.

The current Context constructor was exercised from the restored source-context
with Python 3.14.6, PyYAML 6.0.3 and cryptography 46.0.3: 20,794 units and 77 technical
retentions. Historical job queues/model prompts and redundant analysis exports are
not resumed by recovery. New editing still follows the retained authoring rules.
Two original decoded game textures were absent before this audit; the private
manifest records their hashes. Future regeneration of those textures requires the
matching original game. This does not block the verified normal installer rebuild.

## Normal installer rebuild

The accepted 1.0.0 frozen payload is recovered from the existing public Windows
release, using all 7,048 file hashes in `archival-inputs.json`. No old working
folders, previous locale ZIPs or model jobs are needed for the normal rebuild.
The builders restore this exact payload automatically if absent:

```sh
OMORI_RELEASE_DIR="$PWD/dist/NEW_MAC_REVISION" zsh installer/Scripts/build-mac.sh
OMORI_RELEASE_DIR="$PWD/dist/NEW_WINDOWS_REVISION" zsh installer/Scripts/build-windows.sh
```

Use fresh output paths. macOS requires Swift/CLT and the macOS SDK; Windows
cross-compilation requires Homebrew MinGW-w64, make and zip. The pinned zlib C
source is retained. `OMORI_SWIFT_SCRATCH_PATH` optionally selects a fresh build
cache inside the project. Build provenance remains available through
`installer/Scripts/build-provenance.py`; it checks a clean pushed source revision.

The initial restore and complete normal builds for both platforms passed during
the 2026-11-03 archival audit. Restoring existing release bytes is recovery, not
new runtime/editorial acceptance or publication. Original games, player saves,
credentials, obsolete screenshots and whole historical work folders are excluded.
PreservedSaves remains protected owner data. Remove generated payloads, build
caches and distributions again after final verification.
