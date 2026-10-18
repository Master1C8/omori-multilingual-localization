# OMORI multilingual localization

Native Windows and macOS installers and development tools for the VN Revival
OMORI localization. Supported Steam application: **1150690**; supported game
content build: **8879120**.

The installer includes 27 languages, installs their isolated packages, and lets
the player select the active language. Players need a licensed copy of OMORI.
No model account or API key is required.

Download the installer from [VN Revival](https://vnrevival.fun/ru/games/omori).
See [installer documentation](installer/README.md) for the package format,
build steps, protection of existing mods and saves, and validation boundaries.

This repository contains installer and tooling source. Original game assets,
extracted text, private task journals, local test evidence, and generated release
archives are excluded. Full localization editorial review and native Windows
gameplay verification remain separate from the existing native macOS visual
checks and installer fixture tests. This project is unaffiliated with OMOCAT.

For a release assembled from completed native-QA records, use
`installer/Scripts/assemble_reviewed_payload.py` with the pinned final-inputs
and completion files, then pass its output to the existing platform build
scripts. It selects each locale's exact tested row, verifies the reconstructed
bytes, and retains that locale's editorial status. A later single-locale test
payload must never replace the complete tested language set.

Third-party components retain their own license notices, including zlib under
`installer/vendor/`. No license grant is made for the original game assets.
