# Source-only archival

The laptop retains canonical editable source and Git history, authored translations,
approved glossaries, runtime JS, editable fonts/licenses and editing instructions.
Player saves are protected separately. GitHub holds the existing accepted macOS and
Windows 1.0.0 installers and a checksummed maintainer-only minimal source/input draft.
See [recovery](Documentation/RECOVERY.md) for restore and normal build commands.

The public repository remains writable and its history/visibility are preserved.
No game, model queue, deployment or publication was started during archival.
Historical acceptance is retained; this audit does not claim a fresh gameplay test.

Final local cleanup is pending one obsolete root-owned runtime-check directory:
`dist/installer/1.0.0-provenance-20261020-02/runtime-check`. Ordinary user write
access is unavailable. All independently writable generated data is retired after
verified recovery; the privileged subtree is preserved in place pending the narrow
fingerprinted administrator cleanup in ProjectStorageAudit.
