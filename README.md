# OMORI — VN Revival Translation Installer

Native Windows and macOS installers for the VN Revival OMORI localization.
The shared package contains 27 languages; the installer selects one active language
while preserving the isolated packages. A licensed Steam copy of OMORI is required:
application **1150690**, supported content build **8879120**. No model account or API
key is needed to play with this standard localization.

Windows uses a native x64 installer; the macOS application supports Apple silicon
and Intel. Extract the whole Windows ZIP, retaining `Resources` beside the EXE.
Close OMORI, open the installer, choose a language and install, then launch via Steam.

## Installation, recovery and development

Read [installer documentation](installer/README.md) for discovery, package format,
source build commands and recovery. Keep `.vnrevival-omori` in the game's resource
folder: it holds original backups and the recovery journal. Unknown changes block
replacement; do not delete recovery data to force installation. Saves are outside
the installer's permitted resource paths.

This repository is the installer/tooling source for the distributed OMORI mod.
Localization Workbench is a separate development product, not this installer and
not proof of the source revision used for a downloaded archive. Its maintenance is
outside this project's release task. Do not use its repository HEAD as mod provenance.

[Windows 1.0.0 and its build evidence are published](https://github.com/Master1C8/omori-multilingual-localization/releases/tag/windows-1.0.0-e7b6c0e32828).
Follow [release verification](Documentation/release-verification.md) to download the
installer, compare checksums and identify its exact source commit without running it.
Original game assets and the retained translation payload are not published in this
source-only repository. The build record identifies those local inputs by hashes;
public installer source alone is not enough to reconstruct the complete package.

## Downloads and project links

- [Download and installation instructions](https://vnrevival.fun/ru/games/omori)
- [VN Revival project](https://vnrevival.fun/info/about)
- [Application privacy and security](https://vnrevival.fun/info/app-security)
- [Source repository](https://github.com/Master1C8/omori-multilingual-localization)
- [Report an issue](https://github.com/Master1C8/omori-multilingual-localization/issues) — include OS, game version, release version and archive SHA-256; omit saves, credentials and private logs.

## Authorship and verification

Maintained by [Anton / Master1C8](https://github.com/Master1C8) for VN Revival.
Codex is an AI development and translation tool, not a human editor. Human review,
Codex-assisted work and automated checks are separate activities; historical
receipts describe only the work and revision they actually cover.

Use the exact downloaded file's checksum and any recorded source-commit/build link
on the game page. The repository's latest branch is not evidence of an older
archive's source. SHA-256 proves byte identity; it is distinct from publisher
signing, Apple notarization, a build attestation and an independent security review.
This project is not affiliated with the original game's developer.

[Historical working and build notes](Documentation/README-history-2026-10-20.md)
are retained unchanged for development traceability. They do not replace the current
download instructions or establish the provenance of newly generated files.
