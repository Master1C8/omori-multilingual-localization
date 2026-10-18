# OMORI shared CLI binding, revision 1

This is the common binding for the fixed universal stages. It supersedes the old
Russian binding only for new multilingual work; it does not edit historical recipes
or transfer Russian wording, audits or runtime acceptance. Sources are English,
Steam build 8879120. The project has no Git and no repository must be created.

**Current preparation is incomplete.** Read `source/multilingual/CHECKPOINT.md` and
`source/multilingual/acceptance.json` before locale work. Both shared gates remain
`needs-review`. The exact 20,794-record inventory and plaintext adapters are verified,
but complete special-scene source coverage and a neutral native display compiler
still need work. Do not start locale mass translation on the old acceptance or on
these technical no-op fixtures.

## Invocation and frozen tooling

The caller supplies the canonical project and source data roots. Tool code may run
from the supervisor's frozen tooling directory. It never infers the project root
from `__file__`; only sibling tool dependencies use that location. Do not copy a
project checkout or call old Russian tools as a fallback.

```sh
PROJECT='/Users/antonkrutov/Desktop/omori full translation mod'
MASTER='/Users/antonkrutov/Desktop/SiteForMods'
TOOLS="$PROJECT/tools/multilingual"
# After supervisor freeze, set TOOLS to the frozen directory instead:
# TOOLS="$PROJECT/runtime/cli-localization/runs/20261014T124749Z-facf4e91/tooling"
DATA="$PROJECT/source/multilingual/shared-8879120-03"
LOCALE='es'  # Set explicitly to the assigned siteLocale, never infer it.
WORK="$PROJECT/runtime/multilingual/locales/$LOCALE"
YAML_MODULE='/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw/js/libs/js-yaml-master'
CLI=(python3 -B "$TOOLS/locale_tools.py" --project-root "$PROJECT" --data-root "$DATA" --locale "$LOCALE")
```

The `CLI` array is supported by the workstation zsh shell. All 26 target rows
come from the canonical 31-language catalog referenced by `renderer-matrix.json`.
`en/zh/ja/ko` are official and excluded; `ru` is already owned by another delivery.
`es` and `es-419` stay distinct. Serbian uses Cyrillic. Missing, unknown and excluded
locale selections reject before writes. Locale outputs must resolve inside
`runtime/multilingual/locales/<siteLocale>/`; symlinks cannot escape this boundary.
Each locale owns only that directory. Shared files remain preparation-owned.

## Stages and actual available commands

| Fixed stage | Command | Gate/result |
| --- | --- | --- |
| scope | `"${CLI[@]}" scope` | Explicit game/build/type/locale and process binding. |
| probe | `"${CLI[@]}" probe` | Read the applicable shared matrix. Accepted-static applies to unverified paths; failed mechanisms still block. |
| source | `"${CLI[@]}" source-check` | Exact inventory combination and source metadata; `needs-review` is not acceptance. |
| glossary | `"${CLI[@]}" glossary-check --master-root "$MASTER" --glossary-snapshot "$WORK/glossary/snapshot.json"` | Current canonical English reference, full target ID/order, unchanged files and two clean reading-layer evidence bindings. |
| translate-edit entry | `"${CLI[@]}" case-check --master-root "$MASTER" --glossary-snapshot "$WORK/glossary/snapshot.json" --decisions "$WORK/special-scenes/decisions.json"` | Every discovered case needs actual reviewed target wording and settled effect/solution/identity/adapter contracts. |
| translate-edit batches | `"${CLI[@]}" validate-batch --master-root "$MASTER" --glossary-snapshot "$WORK/glossary/snapshot.json" --decisions "$WORK/special-scenes/decisions.json" --batch "$WORK/batches/BATCH.json"` | Source, glossary, decision and explicit locale pins; immediate edit, controls, retentions and codec checks. |
| translate-edit assembly | `"${CLI[@]}" assemble --master-root "$MASTER" --glossary-snapshot "$WORK/glossary/snapshot.json" --decisions "$WORK/special-scenes/decisions.json" --batch-dir "$WORK/batches" --yaml-module "$YAML_MODULE" --output "$WORK/build/NEW_REVISION"` | Merge all current batches from original snapshots once, then actual plaintext/native-parser readback. |
| translate-edit progress | `"${CLI[@]}" progress --batch-dir "$WORK/batches" --build-dir "$WORK/build/REVISION" --yaml-module "$YAML_MODULE"` | Draft counts plus delivered revalidation against current authors; zero semantic credit. Without `--build-dir`, delivery is unverified. |
| editorial | `"${CLI[@]}" stage-check editorial` | Currently rejects: common immutable cycle/closure and independent-review adapters are not implemented. Follow the universal protocol; never substitute this rejection or a validator for review. |
| resources | `"${CLI[@]}" stage-check resources` | Currently rejects: target fonts, name-input layouts, shaping/bidi repairs and integrated display compiler are pending. Textures/images/OCR are excluded by this assignment. |
| package | `"${CLI[@]}" stage-check package` | Currently rejects: neutral native encrypted-overlay packaging/readback binding is pending. OneLoader is superseded. |
| runtime | `"${CLI[@]}" stage-check runtime` | Not-run; native boot/visual/game/save/installer checks require separately applicable authorization. |
| delivery | `"${CLI[@]}" stage-check delivery` | Currently rejects: no finished local locale delivery or shared-prepared claim. |

The rejecting stage bindings document missing capability, not successful execution.
They must be completed during shared preparation before this binding is accepted.
Do not replace them with old Russian commands or silently mark them passed.
Missing later fonts/packages do not imply complete local delivery.

## Bounded source and case reads

```sh
"${CLI[@]}" queue --offset 0 --limit 15
"${CLI[@]}" source 'languages/en/XX_GENERAL.HERO' --offset 0 --max-chars 18000
"${CLI[@]}" case-index
"${CLI[@]}" case-source OMORI-SP002 --offset 0 --max-chars 18000
```

Read every necessary page at the returned `nextOffset`; no row is truncated. Increase
the explicit bound when one whole row cannot fit. Source pages retain full original
fields, typed paths, exact source spans, context and decoded-source metadata. Queue
entries include scalar, display, note, embedded-program and direct-script adapters;
harder families are never omitted. Catalog adjacency is not consumer dialogue order.
Inspect complete branches, real callers and neighboring scene context where needed.
Case reads omit Russian locale decisions. The old registry's 26 cases/829 members
are targeted discovery, not exhaustive semantic coverage or locale acceptance.

## Glossary dependency contract

The separate glossary owner owns source and all target glossary revisions. Do not
write `glossary/` or master data here. Request/use that owner's current reviewed
integration packet. Begin glossary work with `"$MASTER/vnrevival" glossary guide`
and `"$MASTER/vnrevival" glossary work omori "$LOCALE"`; content reads use only
`./vnrevival`. The shared tool calls `glossary size omori --json` to get the CURRENT
canonical English reference hash. It does not read master content files directly.

At this checkpoint the 699-entry canonical English raw hash is
`e8391d780e4511fe63261a234ec8b1c3c51cd3242493b3c40db1704f8781097b`;
the compact source-reference-v1 hash is
`d63c1690597b181c40e89a87619616d1a9fe61d22e8bc6e44575d53103b1cdf3`.
These are different representations. Recheck through the CLI on every relevant
resume. Old accepted definitions are not current merely because IDs/counts match.
A changed source reference needs dependency reconciliation by the glossary owner;
do not re-pin old target readiness mechanically or modify the canonical source.

`snapshot.json` uses explicit `siteLocale`, `sourceLocale: en`,
`sourceReferenceSha256`, `sourceFile`, `targetFile`, `sourceSha256`, `targetSha256`,
`sourceReadinessFile`, `targetReadinessFile`, and both readiness SHA-256 values.
Paths resolve relative to the snapshot. Source and target are ordered entry arrays
(source may use an `entries` wrapper). Each entry has `id`, `term`, `meaning`.
Both readiness receipts declare `status: accepted`, `standard: standard`,
`artifactSha256`, the current `sourceReferenceSha256`, `unresolved: []`, and exactly
two layers. Each layer declares `status: complete-clean`, the complete ordered
`actualReadIds`, `dimensions: [fidelity, native-language]` and reviewer identity.
An adapter from the existing glossary owner's receipt format is still pending;
do not fabricate receipts to meet this schema. Scripts only bind evidence; counts
and self-authored flags never establish an actual reading or semantic correctness.

Load one complete approved compact working glossary once per continuing translation
context. Open detailed evidence only for a concrete unresolved issue. Character
evidence/address strategy must be resolved under the standard gate before game text.

## Author special-scene decisions first

After source/adapters and glossary gates pass, prepare and review ALL discovered
in-scope cases before ordinary batches, even if the first ordinary scene is unrelated.
`decisions.json` binds `siteLocale`, `inventorySha256`, `glossarySnapshotSha256`,
`registrySha256`, `targetNamebox` (approved ROBOHEART term) and a `cases` array.
Each case has its exact registry `id` and `unitIds`, `status: reviewed`,
`unresolved: []`, `authoredFile`, `authoredSha256`, reviewer, effect/solution,
identity/adapter contracts and concrete positive/negative scenarios. Field names are
`effectOrSolution`, `identityContract`, `adaptationContract`, `positiveScenario`,
`negativeScenario`, `reviewer`. Authored files contain `entries` for the complete
clue/answer/distractor/feedback/dependency group, with actual accepted targets.

A registry, a generic "adapt later" route, guessed solution or unknown adapter
feasibility cannot pass. Keep branches/input/resource names native. Preserve bad
verse, intentional wrong grammar, language-learning words, hiddenness/redaction timing,
foreign-language role and source anomalies. Final textures and authorized runtime QA
are later gates. A newly found asset/case reopens the shared source gate and relevant
dependency closure for every started locale; never create a private locale inventory.

## Authoring, exact structure and delivered output

Batch JSON binds `siteLocale`, `sourceLocale: en`, `inventorySha256`,
`glossarySnapshotSha256`, `specialSceneDecisionsSha256`, `targetNamebox` and `entries`.
Each entry has the exact original `id`/`source`, directly model-authored `target`,
and `immediateEdit: true` only after an actual paired immediate edit. Keep untranslated
technical IDs, command keys, numbers, controls and logical literals unchanged.
Source ID includes typed array indices and occurrence multiplicity; equal strings
are not interchangeable. Do not generate wording, translate through Russian or use
external translation services/models.

All 77 technical retentions remain source-equal. They are separate from the 20,717
visible-text denominator: 17,212 scalar/spanned text plus 3,505 addressed display labels.
All 20,794 records remain in the shared accounted inventory. Source-equal visible
wording needs individual contextual justification later, not automatic completion.
The common numeric guard currently requires exact source presentation for every
locale; no Russian number-format exception is inherited.

Display mappings carry exact asset/path or AST span identity; original logic names
remain unchanged. The sidecar is not yet integrated into a neutral native compiler.
Mixed notes are spliced at original spans, retaining every gap/tag/suffix. JS spans
use UTF-16, not Python codepoints; delivered literals are reparsed at adjusted spans.
Embedded 355/655 programs retain physical line paths/cardinality and protected parents.
Ordinary and embedded edits in one resource merge once so one batch cannot erase another.
Blank visible AST fragments require a direct, exact source-bound
`syntacticOmission` with `kind: grammatical-fragment`, `sourceValueSha256`, `reason`.

Nine encoded dialogue IDs use source-bound metadata: `encodedPayload` has codec,
source discovery hash, decoded source/target, exact line-break count and target namebox.
Use the copied `encoded_dialogue.authored_encoding` primitive to serialize model-authored
decoded text. It generates no wording. Preserve outer speed/frame/LF and inner LF;
battle message_127 has an inner terminal LF and message_128 alone has `<br>`.

Assembly reads actual source snapshots and native YAML values, rejects duplicate edits,
compares protected full trees and reinserts exact spans. Native YAML key types/order
are preserved from original YAML; JavaScript's string-key/integer-order projection is
explicitly reconciled, with ambiguous key collisions rejected. The single protected
Notes trailing newline is retained from the native parser, never silently trimmed.
The parser module is original-graph hashed. No installed overlay supplies source text.

Outputs are plaintext with original asset names plus `.plaintext.{json,yaml,js}`.
They are technical build inputs, not encrypted/native playable packages. A new output
directory is immutable. A between-file failure leaves a partial revision with no
completion receipt; preserve it, record the failure, reconcile, then use a fresh
revision. There is no cross-file transaction or accepted partial retry. Progress with
`--build-dir` reconstructs expected bytes from current authors and rejects altered
protected data, targets, sidecars, extra files and forged receipt hashes.

## Editorial and later resources

Use the one universal audit protocol pinned in `process-binding.json`: complete
deterministic preflight, one complete semantic source-to-target audit, corrections,
immutable changed/closure/component lists and read rows, independent dependency-aware
diff audit, correction deltas, mandatory regressions and final deterministic gate.
Semantic coverage requires actual all-unit reading. Independent review requires a
distinct reviewer and applicable authorization; a self-reread or validator is not
independent. Preserve clean unaffected evidence only under the universal invalidation
rules. Never weaken or invent another editorial acceptance algorithm.

Native05's bootstrap order, narrow legacy serialization normalization, save/load
pointer-width reservation and title Bitmap+Sprite sizing have common static helpers
and original-consumer controls. Their common native integration still needs completion.
Database/map/save labels, dynamic variable provenance, both password producers,
contextual forms, pizza image-key consumer, glyph probes and locale input layouts must
not be omitted. All need final authored/source/version bindings and delivered checks.

The renderer matrix records `ar/fa/he/hi/th` as baseline-mechanism blocked. Per-code-unit
dialogue drawing fails their run/cluster/bidi requirements. Significant run-based
renderer work needs owner agreement; accepted-static does not override a demonstrated
failed mechanism. Other 21 locales are unverified with the accepted-static risk decision,
not font/rendering-passed. Cmap alone is not proof. All final fonts/packages and native
boot/visual/gameplay checks remain separate. No launch, installation, save changes,
images/OCR, publication, push/deployment or server lifecycle action is authorized here.

## Resume and reports

At each resume compare source inventory, process binding, matrix, glossary revision,
author and delivered hashes. Reuse immutable verified no-op and unchanged boundaries;
do not rerun full source extraction or read another locale's full translation by default.
Continue the exact pending work in `source/multilingual/CHECKPOINT.md`.

Every locale report retains all fixed stages and separate statuses for source, glossary,
translated-and-edited visible IDs, technical retentions, complete semantic coverage,
independent diff/deltas, fonts/textures, native build/package, runtime/visual and delivery.
State unmet gates, precise blocker and next action. No percentages inferred from file
counts, flags or technical records. No telemetry is exposed for this preparation request;
record usage as unknown, never estimate it from file sizes. No agents were launched.
