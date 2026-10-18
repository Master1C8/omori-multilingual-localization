# Complete the shared OMORI native delivery adapter

Owner authorization: repair the autonomous CLI localization queue, finish usable local
localizations, then automatically process the remaining languages. Up to six concurrent
fresh Codex CLI jobs total; assigned model GPT-6.1 Sol/high. This is one shared engineering
assignment, with no inherited chat history. Do not launch agents, chats or other models.

Canonical project: /Users/antonkrutov/Desktop/omori full translation mod (intentionally no
Git; do not create a repository). Read the mandatory references in
/Users/antonkrutov/.codex/instructions/sitefor-mods.md, game-localization-prompt.md and
game-localization-audit-workflow.md. Use English for operational output. Existing owner
decision permits static-first translation and accepts unverified in-game rendering.
No installed-game/save changes or game/installer launch; no publication/deployment,
server lifecycle, master/glossary changes, Russian output changes or source inventory changes.

Write ONLY new shared delivery implementation and tests under tools/multilingual/delivery/
and tools/test_multilingual_delivery.py, technical work/checkpoints beneath
runtime/multilingual/shared-delivery/, and staging beneath build/multilingual-delivery/.
Other locale writers are separately owned. Do not change localization_cli.py,
localization_pipeline.py, CLI_LOCALIZATION.md, tools/cli-localization/ or the executing
frozen tooling under runtime/cli-localization/runs/. The coordinator owns these.

Required outcome: a reusable explicit-locale command that compiles existing authored
plaintext plus typed display mappings into the game's real native encrypted overlay,
packages it and verifies actual decompressed/decrypted delivered bytes and bindings.
Implement and test it, rather than only writing a design or inventory. All 26 locales
must use the same adapter with explicit locale configuration; reject official/ru/unknown
locales before writes. Keep linguistic acceptance separate; a technical build may be a
candidate, final delivery needs the coordinator's accepted editorial evidence.

Inputs and existing verified mechanisms:
- source/multilingual/shared-8879120-03/units.json: 20,794 original IDs; SHA256
  4faf2a7b0bc682febcbcb03fe67ea7c2cad1ead21723ba5ae47c6f33d265214d.
  technical-retentions.json has77 separate technical IDs; visible denominator20,717.
- tools/multilingual/locale_tools.py and frozen run tooling-direct-v2 build323 plaintext
  resources and3505 addressed display mappings. They preserve original logic names but
  deliberately leave integration pending-native-display-compiler.
- Complete plaintext examples: runtime/multilingual/locales/es/attempt-0043-plaintext-01,
  de/editorial-corrections-0029, fr/attempt-0028-candidate-plaintext-01. Read receipts;
  do not trust stale paths or transfer another locale's wording.
- Read existing tools/compile_ru_display.py, tools/build_ru_direct.py,
  tools/package_ru_direct.py and runtime/ru-engine-display.js as technical references
  only. Russian files are read-only; reuse proven mechanisms parametrically, do not
  inherit Russian wording/grammar/fonts/name-input decisions or import hardcoded ru tools
  as the generic builder. Original snapshot assets are under source/inventory-8879120-01/
  and native YAML supplement; installed original js-yaml may be read, not modified.

Necessary behavior:
1. Merge scalar/JS/event edits without erasing earlier authored text. Wire every typed
   display mapping to its actual consumer, preserving internal identifiers and gameplay
   logic. Shared typed bindings should handle actor/item/enemy/map/note/variable fields,
   joined dynamic messages, native YAML captions and selected font/locale configuration.
2. Keep explicit locale metadata and fonts configuration. Inspect actual rendering needs;
   do not claim RTL/shaping/actual rendering from cmap or fixtures. Implement routine
   integration; record concrete unsupported mechanism boundaries rather than inventing
   completeness or silently passing English through. No new font download if a suitable
   verified font already exists. Use fonts skill if materially needed.
3. Source identity, exact protected-value preservation and complete authored-to-delivered
   binding are gates. Reopen actual archive/decrypt native resources, verify actual entry
   set/bytes and all mapped targets. Merely searching a ZIP for target substrings fails.
4. Existing outputs are immutable revisions. Safe paths and duplicate IDs are enforced.
   Failure between writes leaves an explicitly incomplete revision with no acceptance;
   do not claim a multi-file transaction. Package must include only needed override files,
   not redistribute all original game assets. Preserve other locales.
5. Add meaningful tests: explicit-locale rejection before writes, wrong-locale mapping,
   stale source/author receipts, protected logic mutation, incomplete/unwired mappings,
   archive tamper/extra entries, and successful compile/package/decrypt/readback against
   real existing locale data. Distinguish mocked consumer checks from actual game runtime.

Proposed stable entry point (coordinate only through saved contract):
python3 -B tools/multilingual/delivery/native_delivery.py --root PROJECT --locale LOCALE
  build --plaintext DIR --output NEW_REVISION
Same entry: verify --build REVISION; package --build REVISION --output NEW_ZIP.
If a different interface is necessary, save exact commands/receipt schemas in
runtime/multilingual/shared-delivery/CONTRACT.json and CHECKPOINT.md immediately.
Coordinator will freeze your complete helper dependency closure after you finish.

Work through implementation and actual local candidate verification. If a concrete
mechanism cannot be safely completed, save implemented work, exact failing boundary and
remaining actions. Do not repeat unchanged inspection/checkpoints as model progress.
Return local-scope-complete only for implemented verified adapter; blocked for a precise
external obstacle; continue only for concrete remaining implementation with saved code.
Every evidence item is an existing file path, no telemetry prose. Report request usage
as unknown if unavailable; coordinator collects terminal CLI telemetry.
