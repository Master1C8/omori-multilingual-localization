# OMORI shared native delivery adapter

The explicit-locale adapter builds **technical candidates** from current authored batches
and an already assembled plaintext revision. It does not author translations or grant
editorial acceptance. It uses the pinned 8879120 snapshot, the shared 20,794-record
inventory and the separate 77-record technical-retention manifest.

```
python3 -B tools/multilingual/delivery/native_delivery.py --root "$PROJECT" --locale es build --plaintext "$PLAINTEXT" --output "$PROJECT/build/multilingual-delivery/NEW_REVISION"
python3 -B tools/multilingual/delivery/native_delivery.py --root "$PROJECT" --locale es verify --build "$REVISION"
python3 -B tools/multilingual/delivery/native_delivery.py --root "$PROJECT" --locale es package --build "$REVISION" --output "$PROJECT/build/multilingual-delivery/NEW.zip"
python3 -B tools/multilingual/delivery/native_delivery.py --root "$PROJECT" --locale es verify --build "$REVISION" --archive "$ZIP"
```

Use the same command for all 26 configured locales. Official locales, Russian and unknown
codes fail before writes. Input revisions must belong to the selected locale under
`runtime/multilingual/locales/LOCALE`; current authors live in `translation/LOCALE/batches`.
All outputs are confined to `build/multilingual-delivery`. Existing revisions are immutable.
The process never starts a game or installer and never modifies installed assets or saves.

`locales.json` supplies explicit resource channel, direction, script, font roles, keyboard
extensions and known mechanism boundaries. It references the existing renderer decision;
it does not replace the canonical language catalog. The native EN resource channel remains
EN internally. A first bootstrap plugin installs protected core function overrides before
native plugin aliases are captured; the last plugin installs typed presentation hooks and
font readiness. `js/plugins.js` preserves the original plugin sequence and authored
parameters between those two additions.

`compiler.py` merges scalar, note-fragment, JS-literal and embedded-event edits against
their original parents once. Technical `consumers.json` contains reviewed exact source
expressions/spans. Database names, error messages and variable values remain native;
source-bound display functions resolve authored labels at consumers. Native password
catalog commands translate display values back to their original tokens before logic uses
them, with separate typed display provenance. Grammatical reordering or inflection is an
authored/editorial concern, not an automatic locale guess. The AFRAID operand remains raw
for branch selection; that branch returns its separate authored sentence.

Original game font identities are checked against `source/font-reference/inputs-8879120.json`.
The retained fontTools 4.60.2 environment is reused. Existing original fonts provide primary
glyphs, and scoped fallback CSS uses retained Noto bytes only for missing codepoints.
Supplemental Thai/Arabic fonts were separately downloaded from exact official Google
Fonts commits with retained OFL licenses/provenance; normal builds never download fonts.
`script-fonts.json` pins every supplemental font, license and provenance file, and these
inputs join the actual native recipe dependencies. Font tables, metrics and cmap coverage are static evidence; outline
quality, actual loaded faces, shaping, bidi, cluster placement and readability remain
unverified unless separately evidenced. Font coverage gaps cause an explicit failure,
never transliteration or an English fallback. The discovery renderer matrix remains
immutable historical evidence. A versioned delivery adapter can repair a documented
mechanism without relabeling its original probe as passed. Thai, Hindi and Hebrew
retain their separate recorded script constraints; a font alone cannot close them.

## Arabic-family static repair

Delivery v3 configures `arabic-context-runs-v1` for ar/fa. The last install plugin wraps
the final native Window_Base normal-text path and Bitmap.drawText; whole contextual
runs reach Canvas with transient Unicode RTL embeddings instead of isolated code units. Runs end before
native escape/newline/page commands. Soft wrapping consumes no logical character and
does not split an Arabic word or its marks. Native controls retain their indices and
side effects. Icon positions mirror the same logical advance. Distinct native x origins
remain distinct mirrored columns. Arabic text gets additional line-height allowance.
TDS receives one shaped run per effect sprite; the legacy name field draws its whole
logical name, while native name storage, validation and confirmation stay logical.
The configured Arabic default keyboard retains native controls and Latin shift input;
its fifth row is reached through the existing selectable-window scrolling.

This is a bounded presentation adapter, not a replacement engine. Typewriter and
letter effects now operate per contextual run, not per code unit. Canvas joining/bidi,
loaded faces, cross-style bidirectional ordering, actual font sizes, wrapping, portrait
placement, input/scroll interaction and readability remain subject to the owner's
deferred runtime/visual QA. The isolated Node tests record Canvas calls and preserve
command boundaries; they do not render pixels or prove in-game behavior. The actual
native build still validates all protected resources and every delivered byte once.
Do not remove the original blocked receipt or claim runtime passed from this build.

Delivery v4 preserves joining context across nonprinting inline style/pause commands.
The exact current Arabic corpus has108 such joining boundaries in78 IDs; the broader
corpus test inspects all17444 inline boundaries across20719 authored records. The
Unicode16 DerivedJoiningType table distinguishes dual/right/nonjoining letters and
transparent marks. Transient U+200D context controls appear only in Canvas/effect-run
arguments; they never enter authored strings, native command indices, names or saves.
Whitespace, icons, hard breaks, nonjoining letters and explicit ZWNJ stop joining.
The packaged Arabic font explicitly covers the virtual join control. Copyright/license
and source fingerprint are retained in the generated `arabic_joining.js`; regenerate
and check it through `tools/build_arabic_joining.py`. Font-size changes reserve the
native maximum line height once through inherited aliases. Cross-style ligature/bidi
appearance still requires actual runtime QA; Unicode assertions do not render pixels.

The verifier reconstructs canonical plaintext from receipt-bound current authors, recompiles
native bytes, compares the exact entry set, reopens ciphertext with the native AES-CTR
codec and compares every decrypted byte. Native YAML is parsed using the installed original
js-yaml module, read-only, with the shared parser pins checked. Native scripts are parsed
with Acorn. `check_consumers.cjs` exercises every mapped label using decrypted delivered
records and isolated display helpers. It does not test native loader/boot order, gameplay,
Canvas, name input interaction, font loading or visual rendering.

`INCOMPLETE.json` is the revision creation marker. `ACCEPTANCE.json` is written last after
successful actual-byte checks; absent acceptance means incomplete. There is no cross-file
transaction or rollback. Interrupted revisions must be preserved and a fresh path used.
A ZIP is created exclusively, DEFLATE-compressed and then reopened. Duplicate/extra/missing
entries, symlinks, changed bindings, stale source/author/recipe receipts and altered
ciphertext fail verification. A package receipt is a sibling of the ZIP and is issued only
after full decompressed/decrypted verification. The ZIP contains only the override files
and three technical evidence files.

Run the focused suite with a fresh staging path:

```
python3 -B tools/test_multilingual_delivery.py --output build/multilingual-delivery/NEW_TEST_REVISION
```

`--unit-only` runs bounded gate tests. The complete suite additionally compiles, packages
and verifies real Spanish authored data and performs archive/resource/binding mutation
checks. Only deterministic unchanged compilation is reused for negative archive checks;
actual archive and native readback always run. The between-write test replaces compilation
with a two-file fixture and tests the real filesystem acceptance boundary.

The coordinator owns the CLI queue integration, frozen dependency closure, editorial
acceptance and final delivery decision. Nothing in this adapter permits publication,
deployment or game launch. Request usage is unknown in the current tool interface.

Legacy save metadata without actor/map provenance retains native labels; arbitrary old labels are not guessed. Newly produced save metadata gains typed IDs. Detailed unsupported/unverified boundaries are saved in `runtime/multilingual/shared-delivery/LIMITATIONS.json`.

Delivery v5 uses U+202B/U+202C only in the final Bitmap draw argument. It does
not depend on Canvas.direction, which the installed Chromium65 gates behind
ExperimentalCanvasFeatures. Verify the exact engine/API boundary before selecting
a renderer. Tests cover an old context without that API and unchanged logical text.
The old engine's DrawBidiText processes Unicode bidi controls; actual appearance
is still explicitly unverified until the owner-authorized deferred game QA.

## Hindi font and input repair

Delivery v6 scopes the unchanged official Noto Sans Devanagari font/OFL to hi, with
source revision and hashes in source/font-reference/Devanagari-provenance-v1.json.
Static coverage includes the actual62 Devanagari corpus codepoints and75 keyboard
characters; GSUB/GPOS and glyph outlines are retained. Add script fonts through the
scoped registry and a new immutable delivery closure; never alter a live frozen helper.

The original normal-character/name path separates code units. The Hindi adapter sends
intact logical runs to Canvas and the native TDS effect bitmap, retaining native LTR
placement and native command dispatch. Six actual style-straddling mark boundaries
paint the complete cluster with its base style; the original escape is dispatched
next, and the already-painted marks are skipped by source index. Logical strings,
commands, saved names and translated wording remain unchanged. Typewriter/effects
operate per contextual run. Native Latin shift remains; the Hindi default keyboard
uses six14-column rows and native selectable scrolling.

Regressions cover intact conjuncts/reordering marks, style-straddling marks/virama,
source indices, wrapping without splitting words, inherited line heights, native
whole-name/effect wiring, actual keyboard layout/validator functions and font probes.
These are static/fixture checks. Real Canvas shaping, font loading, keyboard scrolling,
IME, name underline metrics, dialogue layout and readability remain deferred runtime QA.
Rebuild from the unchanged accepted plaintext once after a material recipe change.
Preserve all historical candidates/receipts and bind a new versioned candidate to the
new resources task; reuse native acceptance for deterministic one-time ZIP packaging.

## Hebrew static repair (delivery-v7)

`he` uses `hebrew-context-runs-v1`: the existing RTL-run implementation is created
with a Hebrew script predicate and with Arabic joining insertion disabled. Its default
Arabic adapter retains its API and behavior; it is covered by the existing9 boundary
groups. Six additional fixture groups check Hebrew combining runs, Latin/digit order,
escape ownership, soft wraps, name display, icon placement and installation isolation.
These record Canvas calls and cannot establish actual Canvas shaping or readability.

The default name keyboard contains Hebrew letters and the required marks/punctuation;
native Latin shift remains available. Logical names and game identifiers are retained.
All20,717 current visible targets passed the complete-corpus font preflight; the32
formerly missing Hebrew codepoints have actual outlines and a positive space advance.
The official Noto Sans Hebrew3.001 variable source defaults to weight100/Thin. The
pinned `tools/prepare_hebrew_font.py` recipe creates a regular400, width100 static face,
renames the derivative to OMORI Hebrew Fallback, and preserves copyright/OFL and mark
positioning tables. Source, derivative, recipe and license hashes are part of the
supplemental dependency binding. Original variable bytes are kept unchanged.

The old v6 closure and all previous locale ZIPs remain immutable. The discovery matrix
is historical and is not relabeled passed. Actual Hebrew readability, mixed-direction
paragraphs across styles, name interaction and in-game loading remain unverified under
the owner's static-first risk decision. The font repair does not grant editorial or
runtime acceptance, and it does not change any translated pair.

## Contextual-run vertical waves

The fifth-screen Arabic native check exposed a distinction left by the original
run adapter: a single shaped TDS sprite moves up and down as one flat block.
That preserves joining but does not produce the requested wave across the text.
The compiler now includes run_wave.js for Arabic, Persian, Hebrew and Devanagari
contextual renderers, and installs it after their existing shaping adapters.
It calls the original TDS renderer once, retaining the complete contextual Canvas
bitmap, logical index, effect range and tags. Native two-pixel texture strips share
that bitmap and receive spatial phases of the original SINV timing/amplitude.
Joining, marks and bidi are never reconstructed from isolated glyphs. Latin,
Thai cluster handling, non-SINV effects and logical typewriter boundaries delegate
unchanged. Native clearing removes every strip through the original sprite list.

Regression: Arabic `بخ!!`, Hebrew marked words and Devanagari conjunct runs must
have one shaped bitmap and varying vertical phases across it, while logical
indices, exact strip coverage and range/inactive/other-effect delegation remain
unchanged. tools/test_run_wave.cjs replaces native Sprite/TDS APIs; it establishes
those wiring/phase invariants, not actual Canvas shaping, seams, clipping or native
visual quality. A full source-bound build, unchanged text/font comparison and real
native animated screenshot are required for acceptance. Earlier fourteen accepted
non-contextual/Thai captures retain their own unchanged packages and evidence.

The canonical strip adapter applies only when every active effect covering the
current run is SINV. Co-active SHAKE, RAINBOW or SINH retains the previous native
whole-run behavior; inactive/out-of-range effects do not disable the repair.
The additional fixture controls check this boundary explicitly. The first Arabic
full/native control uses the preserved v1 helper on the pure-SINV target; the
co-effect guard leaves that exact target path unchanged. New builds use the
canonical guarded helper. No broad combined-effect wave support is claimed.
