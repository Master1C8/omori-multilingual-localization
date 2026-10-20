# Release verification

The published OMORI archives retain unknown source provenance unless an exact
build record proves otherwise. A current repository HEAD must not be assigned
to an older download.

## Prepared local Windows pilot

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

Verify the final ZIP without launching it:

```sh
shasum -a 256 OMORI-Installer-Windows-1.0.0.zip
unzip -t OMORI-Installer-Windows-1.0.0.zip
```

Windows PowerShell:

```powershell
Get-FileHash .\OMORI-Installer-Windows-1.0.0.zip -Algorithm SHA256
```

Compare with `SHA256SUMS` and `provenance.json`. Check the recorded source commit
on GitHub, the recipe at that commit and the payload inventory fingerprint.
CRC/readback checks establish archive integrity; neither hashes nor this record
prove safety, publisher identity, notarization or gameplay acceptance.
The pilot does not replace the published download without owner authorization.
