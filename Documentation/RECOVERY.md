# Editable input recovery

The public Git repository contains installer/tool source. Authored translation
and glossary working data are additionally preserved in a maintainer-only draft
release, without changing the repository's public visibility or publishing private
editorial records.

- Repository: `Master1C8/omori-multilingual-localization`
- Draft release tag: `private-editable-inputs-2026-11-03`
- Asset: `OMORI-Editable-Inputs.zip`
- SHA-256: `840eac6eb5fb6fe239f2a7e165eb03667ca0330bbfe66c3fe9e3ce0913f57ff8`
- Bound source revision: `59742aba3dae878c5527d446c1aa24861a4fd9a3`
- Contents: 16,319 files, 602,451,429 uncompressed bytes, including authored
  translation/glossary records and the editing instructions. The internal
  `_RECOVERY_MANIFEST.json` records each file's SHA-256.

The draft must remain unpublished. Git clone does not automatically download it.
With the owner's authenticated GitHub account, download from the canonical
project root:

```sh
mkdir -p .recovery
gh release download private-editable-inputs-2026-11-03 \
  --repo Master1C8/omori-multilingual-localization \
  --pattern OMORI-Editable-Inputs.zip --pattern SHA256SUMS --dir .recovery
(cd .recovery && shasum -a 256 -c SHA256SUMS)
unzip -n .recovery/OMORI-Editable-Inputs.zip -d .
```

`unzip -n` restores missing files and preserves existing files. Reconcile existing
files against the internal manifest before treating an existing working copy as
the archived version. The archive does not contain the original game, player
saves, machine dependencies or credentials. Regeneration still requires the
pinned original game/extraction described in the retained editing instructions.
This is a storage/recovery snapshot, not a new editorial or runtime acceptance.
