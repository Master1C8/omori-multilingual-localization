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

The exact published 27-language payload is retained locally at
`source/release-payload-1.0.0`. Pass it directly to either platform build script;
no old `build/` or `runtime/` folder is needed. The current distributions, tested
app seed and compact release evidence are in
`dist/installer/1.0.0-site-20261019-02/`. These private local inputs and generated
artifacts remain excluded from this source-only public repository.

Editable game inputs, translations, glossaries and card manifests remain in
`source/`, `translation/`, `glossary/` and `card/`. Unique development code found
in temporary snapshots is preserved under `source/recovered-development-sources/`;
its original paths and hashes are recorded in the release cleanup receipt.
Disposable build trees, run snapshots, test copies, downloaded tools and Python
environments have been removed. Only the latest published Windows and macOS
installer ZIPs remain in `dist/installer/1.0.0-site-20261019-02/`; earlier
per-locale archives, older installer revisions and redundant unpacked stages
have been removed. Screenshots, the tested build seed and release evidence
are retained. The non-playable Spanish (Latin America) review snapshot is
preserved as editable source in `translation/es-419/review-snapshot-0037/`.

Third-party components retain their own license notices, including zlib under
`installer/vendor/`. No license grant is made for the original game assets.
