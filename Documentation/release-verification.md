# Release verification

## Published Windows 1.0.0

The Windows package was published on October 20, 2026. Download the installer
and its evidence from the [published Windows release](https://github.com/Master1C8/omori-multilingual-localization/releases/tag/windows-1.0.0-e7b6c0e32828).
The [VN Revival game page](https://vnrevival.fun/ru/games/omori) offers the same
Windows archive bytes under the filename `omori-windows-e7b6c0e32828.zip`.

Download these three release assets into one directory:

- `OMORI-Installer-Windows-1.0.0.zip` — the complete installer and payload.
- `OMORI-Windows-1.0.0-e7b6c0e32828-evidence.zip` — build records, input inventory,
  source listing and runtime verification evidence.
- `PUBLICATION-SHA256SUMS` — checksums for both ZIP files.

The installer is **52,505,180 bytes** with SHA-256:

```text
e7b6c0e3282874b8b6a9e04c84f581d38166797c30c2472c69ab16b85d97a478
```

The evidence ZIP has SHA-256:

```text
11e4315adca1852288f2b5912fcb823c250317d1fc7cc0da14bddd2899e80c99
```

Verify without launching either executable. On macOS:

```sh
shasum -a 256 -c PUBLICATION-SHA256SUMS
unzip -t OMORI-Installer-Windows-1.0.0.zip
unzip -t OMORI-Windows-1.0.0-e7b6c0e32828-evidence.zip
```

On Windows, compare both calculated hashes with `PUBLICATION-SHA256SUMS`:

```powershell
Get-FileHash .\OMORI-Installer-Windows-1.0.0.zip -Algorithm SHA256
Get-FileHash .\OMORI-Windows-1.0.0-e7b6c0e32828-evidence.zip -Algorithm SHA256
Get-Content .\PUBLICATION-SHA256SUMS
```

Extract the evidence ZIP and compare the installer hash with `SHA256SUMS` and
`provenance.json`. The actual build source is
[`aa4a78fe8b2dd2de5d45a1120fa249c89f2abfbd`](https://github.com/Master1C8/omori-multilingual-localization/commit/aa4a78fe8b2dd2de5d45a1120fa249c89f2abfbd),
not the latest repository HEAD. Match this commit against `provenance.json`,
`vnrevival-release.json`, the embedded installer manifest and the release tag.
Inspect the build recipe at that commit, `source-tree.txt`, `payload-materials.json`
and `build.log` to follow the source and input records. `verification-summary.json`
and `runtime-verification.json` describe their specific verification boundaries.

The evidence retains its original build dates and statuses. Statements about a
prepared local package in those historical records describe the time of creation;
the linked published release records the subsequent publication. Do not rewrite
those records or substitute a later commit for the actual build source.

The Windows record does not establish provenance for another archive; the macOS
release has its own evidence below. Hashes establish
byte identity; this unsigned local build record is not publisher signing, Apple
notarization, a GitHub build attestation or an independent security review.
The retained translation payload is not in this source-only repository, so public
installer source alone cannot reconstruct the complete package.

## Published macOS 1.0.0

The universal Apple Silicon / Intel package (macOS 14+) was published on October 20,
2026 in the [macOS release](https://github.com/Master1C8/omori-multilingual-localization/releases/tag/macos-1.0.0-376615c0a4aa).
Download these assets together:

- `OMORI-Installer-macOS-1.0.0.zip` (53,868,337 bytes).
- `OMORI-macOS-1.0.0-376615c0a4aa-evidence.zip`.
- `PUBLICATION-SHA256SUMS`.

Run `shasum -a 256 -c PUBLICATION-SHA256SUMS` in their directory. The installer SHA-256 is
`376615c0a4aa7024cb93589fb559de3096362e4565e8e2b8b7d20fe9573cea3c`.
The evidence SHA-256 is
`4df96a6442f898568681a5fdd53cd40908f6f75af56e3df65e0875e2f0320c94`.

The actual build commit is
[`0b19348f26390a54b10ef458d0a0bf977866ba60`](https://github.com/Master1C8/omori-multilingual-localization/commit/0b19348f26390a54b10ef458d0a0bf977866ba60).
Compare it with the release tag, `provenance.json` and the installer ZIP's root
`vnrevival-release.json`. Inspect `source-tree.txt`, `build.log` and
`payload-materials.json` for the source and retained payload inputs.
`archive-verification.json` records extracted app verification;
`payload-verification.json` records native reconstruction of all delivered files;
`fixture-checks/result.json` records eight installer test groups.
These checks do not claim a new real-game playthrough. The app uses a verified
ad hoc signature and is not notarized. Historical preparation records retain their
original dates and statuses; the linked release records subsequent publication.
The previous macOS archive's exact source remains unknown.

## Building a future Windows release

Build from committed, pushed canonical main with the retained payload:

```sh
python3 installer/Scripts/build-provenance.py \
  --payload source/release-payload-1.0.0 \
  --release dist/installer/NEW_PROVENANCE_REVISION
```

The recipe rejects dirty source, an existing output directory, payload catalog
mismatch and missing tools. It hashes all payload files before and after the
build, records the exact source commit and tool binaries, compares every ZIP
entry with the final stage, rebuilds zlib from tracked source instead of reusing
an unproven static library, verifies x86-64 PE headers and writes the completion
record last. A failure preserves diagnostics without declaring completion.
The record is an unsigned local statement, not a GitHub build attestation.
The retained payload is not publicly distributed by this source repository.

For a future universal macOS build, use the same recipe with `--platform macos`
and a new output directory. Verify extracted archives in a physical canonical
project path: Foundation may normalize macOS temporary paths through `/var`,
which the installer correctly rejects as a symbolic-link ancestor.
