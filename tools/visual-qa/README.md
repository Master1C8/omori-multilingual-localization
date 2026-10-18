# Native OMORI screenshots with Oculix

## Fourth frame: OMORI equipment

The owner's October 18 video starts from the first save. Load that slot, press X
on the map, select the enabled `equip` command by its native symbol, and confirm
the first actor. Stop when the weapon slot, full item description and statistics
are presented. Do not confirm the weapon slot: that opens the replacement list.
The verified save contains actor1 and SHINY KNIFE weapon2; obtain stable IDs from
the actual saved/runtime state rather than guessing from display names.

`equipment_route.py` shares `MariRoute.load_first_save`; it does not walk to Mari.
The terminal guard rejects another actor, the charm slot, a moving/incomplete help
panel and an active replacement list. `test_equipment_route.py` supplies matching
positive controls and changes each rejection condition independently; these
fixtures replace engine state and do not establish native rendering correctness.
The native route additionally proves the loaded actor and equipment are unchanged.

Prepare each immutable session with `prepare-equipment-run.py`, then use
`mari-session.py --route equipment` or `mari-series.py --route equipment`.
The preparer pins both native binaries, Oculix classes, templates, every Python/JS
dependency and the exact 81 accepted image hashes. Background mode is mandatory;
never activate/refocus the game because the owner is using the laptop.
Each native `<locale>-04-omori-equipment.png` needs visual inspection and a
hash-bound gate from `record-equipment-review.py` before the next locale.

PT fourth-frame series01 reached Splash with the title queued. Observer timers
advanced for about77 seconds while both native RAF count1210 and input serial1606
remained unchanged, despite the focus gate returning true. The startup timeout
rejected the run before input; restoration passed. No SIGKILL was sent: the owned
parent exited before the separately guarded force-close attempt inspected it.

New equipment recipes install `background-frame-adapter.js` before engine/PIXI
scripts. It preserves native animation callbacks when delivered and uses an
unthrottled100ms timer only when delivery stalls. Each request is delivered once;
cancellation and late native callbacks cannot advance the engine a second time.
This is temporary QA scheduling, with delivery counters retained in evidence.
It does not change a packaged game asset. `test_background_frame.cjs` replaces
browser scheduling with controlled queues; a real background native capture is
still required. Regression: timers continue while native RAF stops on another
Space, the title remains queued, and a late native callback arrives after fallback.

Record browser DOM focus separately from native application focus. PT's final DOM
sample reported focus after all12 action receipts proved native `targetActive:false`
with a different frontmost PID. That recipe did not measure final native focus;
retain it as unmeasured instead of inferring it from the browser flag. New fourth-
frame recipes record a native focus sample at capture. Background input rejects
an active game or matching frontmost PID before posting any key, regardless of
the DOM flag. Regression: a contradictory native inactive/frontmost-target pair
must reject; an inactive native game is the positive control.

The legacy first-two-frame route captures the title and save list without
confirming a slot. The Mari and equipment routes load the prepared first save
as described in their route contracts; none writes a save. CrossOver is outside
this native workflow.

The existing installer core switches one locale at a time on the native EN
resource channel. Verify its recorded locale, catalog hash and every owned file
before launch. For the legacy Russian overlay, `adopt-verified-ru.py` accepts only
the exact known installed hashes and recovers all English originals by their
catalog hashes from existing backups. It changes recovery metadata, not saves.

`runtime.py` temporarily adds early-startup and runtime observers to `index.html`, launches
one recorded native process, and restores the original index bytes once the
observer is ready. The observer logs scene, selection, focus and actual keyboard
events. It has no save or game-state command API. Keep its per-run script immutable
until that game has exited. If launch fails before returning, reconcile the
recorded process and surviving children before restoring files or retrying.
Pin `startup-observer.js` alongside runtime.py. It runs before styles/core scripts,
logs resource/JS errors and load milestones to separate startup evidence, and
never performs input or gameplay actions. HU32 remained black before the late
observer appeared; HU33 completed with early diagnostics, but concurrent build
completion changed load conditions, so that success does not establish a causal
startup fix. Preserve both attempts and reconcile processes/restoration first.

Record an action's guarded semantic result before its diagnostic post-action
capture. Derive loaded-slot metadata from that result or the final capture, not
an unconditional flag. No load attempt means false; an attempt without proven
result means unknown. HU32 failed before route entry but the legacy cleanup
receipt incorrectly said loaded; keep the receipt and its correction sidecar.

Oculix's IDE/Jython initialization can fail its Java mouse-position self-test on
this workstation. `OculixMatch.java` calls the same installed Oculix 4.0.0 Finder
engine directly and accepts fresh native RGB image buffers. It performs no mouse
initialization. Run it with `-Djava.awt.headless=true` so image recognition cannot
activate a Java GUI and take game focus. A positive control must match the title
at its actual coordinates (340,69); checking only process exit is insufficient.
Recognition logs identify the engine and record match coordinates
and scores. `vision.py` captures the exact native 640x480-point game content at
1280x960 backing pixels; it removes window chrome without resizing. Only separate
recognition copies are normalized to 8-bit RGB. Review crops never alter final PNGs.

## Control regression

October 17 reproduction: Continue was selected and active, the game had focus,
the keyboard layout was ABC, and the saved binding mapped keyCode 90 to `ok`.
The old global CoreGraphics pulse reached DOM as trusted Z down/up events only
7 ms apart, but the game remained in `Scene_OmoriTitleScreen`. The engine polls
current key state per frame, so such queued down/up delivery can be missed between
updates. This timing explanation is an inference from the event log and engine
input mechanism, not a measured render-tick trace.

The repaired driver uses a private event source, clears modifier flags, supplies
explicit Z text, targets the verified native PID, and holds for 150 ms. In the
matching positive control, the actual received events were 328 ms apart and the
game entered `Scene_OmoriFile`. Each capture guards both the visual marker and the
runtime scene/selected index before input, then guards the resulting scene and
save-list header text. Do not credit event submission alone as a passed transition.

## Rendered ink regression

Canvas advance width is not always the visible ink boundary for RTL labels.
The native Arabic control measured an advance of 119.367 pixels inside a
121-pixel field, yet its actual ink extended beyond the right bitmap edge.
The shared RTL layout helper now measures a detached bitmap with the same
font and drawing settings and positions the actual ink inside the safe margin.
It never changes the saved value or a translation string. Regression coverage
models a 25-pixel right-anchor overhang; native acceptance must also inspect
the whole time label, Latin names and unmodified digit order in each RTL locale.
The same boundary rule applies to the narrow left Save/Load command field:
Persian's longer Load caption exposed clipping there after the file-row labels
had already passed. Preserve the native field size and condensed fitting, but
align its actual ink inside the field. The geometry regression exercises this
compressed RTL command independently and verifies that LTR drawing is untouched.

The detached native font probe compares actual GameFont glyph pixels with the
delivered derived face and with an uncontrolled fallback, and verifies that
ordinary Latin glyphs still use the original game font. Font filenames and
CSS family declarations alone do not establish the rendered face.

## Run and recovery

Use a fresh run directory and an immutable snapshot of `batch.py`, `runtime.py`,
`vision.py` and `runtime-observer.js`. Set `OMORI_QA_PROJECT` to the canonical project
and `OMORI_QA_RUN` to that run. Include compiled native-control, native-window and OculixMatch
artifacts, and record their hashes. Preserve existing accepted PNGs and reconcile
partial outputs before any retry; never enable overwrite implicitly.

Preserve executable modes when copying native helpers (`copy2` plus an explicit
executable check). A hash alone does not establish launchability. Regression:
an identical native-control binary copied with mode 0644 must fail preflight
before installation or Steam launch.

A lost queue driver does not establish that its game exited. Reconcile the exact
recorded parent and children before dispatching another session. When resuming a
verified live route, use a new evidence directory: `Vision` starts its filename
counter at zero, so reusing the old directory would overwrite prior frames.
Keep completed semantic receipts even when the following diagnostic capture was
interrupted. BG series40 resumed its second conversation without another load.
Its recorded game parent later survived the normal SIGTERM timeout while its
renderer became a zombie. Cleanup required rechecking the exact recorded command,
force-closing only that owned parent, then running the pinned restoration adapter.
Regression: vanished driver plus live owned game must block a duplicate launch;
neither a captured PNG nor a dead renderer alone permits resource replacement.

The desktop preflight reads the actual macOS console lock flags. A locked or
unavailable session stops before locale switching; never infer availability from
Accessibility permission alone. In foreground mode, after activation require both
the verified PID and its active/frontmost state. The explicitly selected background
mode below uses process-targeted input without activation. Regression: loginwindow remains frontmost and
IOConsoleLocked is true; no game input or automatic launch retry is allowed.
Do not change screen-lock settings to pass this guard. Read-only observer events
retain original engine errors before a secondary error-printer exception can hide
them; observers do not suppress or recover game exceptions.

Discover windows by the verified native game PID, never by the English title.
The previous Windows-UI test helper matched title `OMORI` or an owner name
containing OMORI; native NW.js uses owner `Game`, while translated System.gameTitle
changes the window title (Arabic: أوموري). It therefore lost a still-running game
after boot. Regression: Arabic title plus owner Game must remain capturable,
while windows belonging to another PID must never be selected. Capture receipts
retain the actual owner PID, title and bounds. Missing filtered windows alone do
not establish that the game exited.

In background mode a window on another macOS Space can retain its owner, number
and exact bounds while `kCGWindowIsOnscreen` is absent. Select the unique native
640x508 window by verified PID and capture that exact window number; do not
activate it or substitute the desktop. Foreground mode still requires Onscreen.
Every capture checks the console is unlocked. Runtime/visual transition guards
and final dimensions remain mandatory. ES14 preserves this regression inventory:
one correct offscreen window plus four menu strips. The selector must accept only
the correct background window, reject a different PID and foreground selection,
accept its visible positive control, and leave duplicate native windows ambiguous.

Set `OMORI_QA_REVIEW_GATE=1` for a supervised batch. After each pair the owned game
stops and the batch waits for a hash-bound `visual-review.json` before installing
another locale. Only an actual review may issue status `pass`.

Launch through the existing native Steam client. Reconcile the unique new native
process with the submitted URI before recording ownership; an accepted request
without readiness is not permission to submit another launch. Direct native
launches were useful for diagnosis, but the production capture recipe uses Steam.

During startup the renderer can pause observer timers for more than three seconds.
Wait on the read-only observer through Boot/Splash before starting repeated native
captures and image matching. Retain the original startup deadline, and require
the actual title marker together with a fresh runtime sample before any input.
ES14 passed Boot/Splash and entered the file scene under this sequence; that does
not establish that capture contention caused the historical Boot stall.
An old sample while waiting through a known splash is not evidence of a failed
transition. Wait within the startup timeout, and require a fresh sample together
with the visual marker before input. Regression: a stale SplashScreens sample
must wait; stale Title/Continue data must never authorize Confirm.

Foreground startup permits one verified refocus and a settling delay. A second focus loss
stops before input and preserves diagnostics. Regression: another application
becomes frontmost again after the successful refocus; no repeated key pulses
or focus-stealing loop may attempt to force the transition.

The batch is sequential. An unexpected state saves diagnostics and stops the
batch. Its cleanup stops only the recorded task-owned native game and verified
children, reapplies Russian through the installer core, compares all original
resource paths and all eight save/settings files byte-for-byte, and archives its
temporary installer metadata inside the project. Do not edit a live run's snapshot
or a dependency it will load later. Visual review remains mandatory for every PNG;
automated recognition does not prove glyphs, spacing, clipping or RTL correctness.

## Background Mari route

`mari-batch.py` requires `OMORI_QA_BACKGROUND=1`. It never activates the game.
The task process temporarily disables the native focus-pause condition and
Chromium's background occlusion throttling; package and entry-point bytes are
restored with concurrent-change guards. These components do not move the player,
load a save or invoke gameplay commands. Input is sent to the verified native PID.
The desktop must still be unlocked. Pin all Python/JS helpers, native binaries,
Oculix classes and image templates in the run before launching it.

Use `native-control ackkey` for each key: down, observed native input sampling and up
must occur in one native process. Separate keydown/keyup subprocesses can hold a
direction long enough to repeat; a short timed pulse can instead be consumed
entirely between engine updates. Regression: one acknowledged Right moves from
(11,16) to (12,16), with the game unfocused, and does not reach (13,16).

The observer delegates to the original Input.update and records the matching
keydown timestamp/key and a fresh update serial before scene logic can clear the
button. CS23 ended its first conversation in Scene_Map, clearing input before the
old frame/pressed predicate sampled it; the driver then held the key until timeout.
New observers require the actual input-update proof or a changed scene. DOM-only,
wrong-key and stale proofs must fail even if rendered frames advanced. The native
driver captures its timestamp and initial state before posting keydown. Failed
acknowledgements retain their JSON/stdout/stderr evidence; never repeat a key just
because the acknowledgement failed. The native self-test exercises matching and
negative controls; real movement/dialogue transitions still require native QA.

The pinned GTP renderer wraps `Graphics.frameCount` modulo1024. A raw comparison
against `keydown.frame+2` can hold a key until timeout across that boundary. The
legacy-observer acknowledgement uses elapsed frames modulo1024. `native-control --test-ack`
exercises one/two-frame wrap, unchanged frame, released input and scene transition
without posting any event. Regression:1023→0 is one frame and must wait;1023→1 is
two frames and must release promptly. Preserve the tested binary in each run.

The authorized route loads slot one, walks Down then Right, and talks to Mari
twice. The first conversation contains internal pause controls; advance by the
actual message state, never a fixed number of confirmations. Select incomplete
quests, then the first quest, and stop with full advice and Mari's portrait open.
No save action is part of this route. Review every third PNG before releasing its
hash-bound gate with `record-mari-review.py`.

Runtime scene readiness does not establish native presentation. Require a fresh
runtime state AND an Oculix marker before input. Regression: the Hindi Quest scene
objects exist while the captured window still shows the previous map/loading
indicator; wait for the stable quest-list frame rather than failing immediately
or sending Confirm. The quest marker contains only fixed UI borders, avoiding
blurred moving scenery. Final advice uses its matching portrait marker.

## Save-slot level spacing

All locale compilers must route the level label and number through the shared
measured `OmoriLocaleUI.drawFileLevel` mechanism. The legacy Russian compiler had
retained two fixed-coordinate draws, so its long Cyrillic label overlapped the
number. Russian now configures the shared helper without installing unrelated
layout hooks. Preserve wording and fonts when repairing this boundary.

Validate the shared layout regression tests and the compiled Russian bootstrap,
then inspect the real native load screen. `measure-ru-level-pixels.py` measures
the actual native PNG text bands, excluding horizontal rules; measurements of
window bitmap rows that include full-width rules cannot establish text spacing.
Audit all 27 locales, including Ukrainian, Bulgarian and Serbian, before claiming
coverage. Preserve superseded accepted screenshots separately and bind their
replacement to old/new hashes. Defer intentional baseline asset/image replacement
until any live batch that protects the original baseline has restored and exited.

After that accepted repair, `mari-batch.py` protects the authorized replacement
hash while still checking the preserved original. `mari-session.py` recognizes two
exact Russian profiles. New catalogs retain the repaired Russian baseline directly;
historical catalogs use a guarded three-file reverse upgrade, immutable capture,
verified cleanup and guarded repair upgrade. At rest the repaired Russian package
must be installed. The original baseline receipt remains unchanged. A failed cleanup blocks the upgrade;
reconcile the exact owned root and surviving child processes first.

The Thai third-frame route exposed a different boundary that menu/load frames do
not exercise: per-code-unit dialogue painting separated SARA AM from its base and
produced a dotted circle. `thai-clusters-v1` groups a base with dependent signs for
normal drawing and TDS effects, preserving native logical text and escape indices.
Wrapping cannot split that cluster. The call-boundary regression contains the
actual SARA AM/stacked-sign case, measurement-only mode, effect drawing and Latin
fallback. It supplements, and never replaces, real native screenshot acceptance.
Retain the rejected frame and corpus boundary audit; do not reuse a rejected PNG
as accepted evidence after changing its filename.

For a long supervised series, `prepare-qa-subcatalogs.py` derives a catalog
containing the selected locale and the Russian restoration baseline. Each locale
row and archive identity remains identical to the verified full parent; compressed
objects are checked and hard-linked without mutation. The receipt retains all27
mandatory locales and the parent fingerprint. These are internal QA catalogs.
`mari-final-report.py` rechecks that lineage. The unchanged installer adapter still
checks all selected files and resource hashes on every application. Dispatch one
session at a time with `mari-series.py`; it records the live child identity and
stops on failure. It never publishes a visual-review pass.

## Compact RTL speaker nameplates

AR series16 exposed a separate surface: the full logical Mari name existed in
Window_NameBox, but dialogue leading placed nearly all of its glyph ink below
the compact bitmap. Preserve that rejected native frame. The shared Arabic/
Hebrew run adapter now renders NameBox through the original rich-text draw path
on a detached bitmap and places its actual ink inside the nameplate, without
scaling glyphs or changing logical text. Native measurement-only and Latin calls
retain their original paths. Grow the nameplate only when actual ink cannot fit;
native refresh still computes its final placement afterward. Restore contents
and release the probe on both success and failure.

`tools/test_rtl_namebox.cjs` reproduces a baseline leaving only two visible rows,
verifies every ink pixel is retained, exercises taller glyphs without scaling,
checks unchanged Latin/measurement controls, and checks empty-probe/native-draw
failures. It replaces Canvas glyphs with a pixel rectangle fixture. New native
AR/FA/HE nameplate captures remain mandatory; geometry tests do not accept them.

## Source-bound quest UI derivatives

The Vietnamese third frame exposed native header/category text rectangles extending
beyond their remaining contents width. Shared quest-label fitting keeps the window
dimensions and native command logic/colors. The native VI09 frame verifies the fix;
the fully rebuilt VI06 package proves that only the initial UI helper in Bootstrap
changes. All other287 resources and the rest of Bootstrap are byte-identical.

`ui_derivative.py` reuses that bounded change for other immutable parent packages.
Its positive control binds the full build, native review, UI source and compiler/
configuration/tool versions. Parent source/author/plaintext hashes, native files,
archive entries and per-locale configuration are verified. The old UI prefix must
match its own source hash; only that prefix is replaced. Historical versions of
three reviewed presentation dependencies are retained in recipe02, while unrelated
dependencies must remain current. New artifacts explicitly retain parent compilation
evidence and use `native-ui-prefix-derivative-v1` verification, dispatched by the
payload preparer. They do not claim a full recompilation or editorial acceptance.

The regression compares all288 derived Vietnamese native resources with the full
VI06 rebuild. A real AES/ZIP fixture with internally matching file hashes but a
source-mismatched prefix must fail specifically at the prefix/source boundary.
Changed positive-control source pins must also fail. Each locale still requires a
real native capture and human review. Directory acceptance follows native-file and
metadata readback; the separate package receipt is written after archive readback.
Interrupted outputs are preserved and require fresh paths.

## Background focus and asset readiness: October18 equipment continuation

`run-fr-03` reached save1 and native OMORI selection, then timed out with an
equipment scene queued. The old observer's `currentBusy` field reads the current
scene's `isBusy()`, not the complete SceneManager gate. Atlas Loader additionally
requires the next scene's atlases and ImageManager readiness; Omori BASE also
blocks on the image request queue. Read queue/cache fields directly rather than
calling atlas predicates, which may load/cache images themselves. New snapshots
record pending URLs/states and next-atlas names, with data-URL payloads omitted.
The equipment transition retains its semantic guard with a bounded180s wait;
asset-loading diagnosis and native acceptance remain pending, not a product fix.

Steam launch can bring the game forward. `run-fr-04` rejected native foreground
input before any key and restored normally. Omori BASE also calls `window.focus()`
unconditionally while plugins are evaluated. The early QA frame adapter now
suppresses that call and counts attempts, before plugins load; the temporary
background manifest also sets window focus=false. A scheduler fixture verifies
that focus attempts never reach the original callback. This does not prove native
focus behavior; every input still requires targetActive=false and a different
native foreground PID. Do not infer native focus from document.hasFocus().

The direct LaunchServices experiment in `run-fr-05` never produced its runtime
observer while a possible macOS notice was foreground. Computer use denied access
to that protected app; its content remains unknown. The owner subsequently reported
removing it. Direct launch then reached the title unfocused in `run-pl-02/03`.
Steam URI still independently activated `series-04/run-pl`, so current background
recipes use `open -g` with the exact verified Steam argument from the successful
PT-BR run. Extra application arguments corrupt the game's encryption key.

Direct background native OS key delivery stalled observer callbacks on the first
pulse in PL02 and PL03. The per-app App Nap diagnostic did not prevent it and was
restored to its original absent key. Do not attribute the failure to App Nap or
repeat that unchanged native-input attempt. No security settings were changed.

Fresh equipment recipes instead compose `input-bridge.js` into the temporary
observer and select `OMORI_QA_INPUT_MODE=bridge`. Requests dispatch untrusted DOM
keydown/up events on the game thread, sampled by three natural `Input.update`
calls and released on the fourth. The bridge delegates to the original update,
never forces engine updates, and exposes no scene/save/equipment command API.
A unique request is never replayed; unsupported keys are rejected. Engine errors
release a held key. `test_input_bridge.cjs` verifies these boundaries with a fake
browser/input fixture; it cannot establish real game input or native rendering.
The real Polish proof is `run-pl-04`: full native visual review passed, all12
requests were sampled/released while native focus remained inactive, and363
Russian resource paths plus8 protected files were restored. Turkish series06
also passed native review with the corrected final SEÇENEKLER letter.
`menu-ui-control.py` binds its fully rebuilt287-resource package and actual
review/installation/restoration to the shared source-prefix derivative recipe.

`bridge-input.py` records actual native focus before and after each request. The
bridge acknowledgement must show release, the matching request/key, three held
samples, and no autorepeat. These are DOM input proofs, never trusted OS keyboard
acknowledgements. All semantic guards, Oculix checks, protected saves and native
visual review still apply. `equipment-final-report.py` distinguishes both input
methods and rechecks their specific evidence. The engine accumulator can call
Input.update several times before rendering; Graphics.frameCount may repeat or
wrap and is diagnostic only. The three sampled pressedTime values must be0,1,2.
Regression: native background key delivery stalls but timers/engine previously
advanced; the bridge advances only the intended UI action, releases, does not
replay, and never activates the app or writes a save.

Historical series04/05 stopped on their recorded rejection; never relaunch them.
Fresh `series-06` snapshots contain the repaired Turkish package and18 untouched
pending locales. Dispatch followed the reviewed/restored Polish proof. Every
locale still needs its own actual visual inspection; the coordinator never issues
review gates.

After a session is fully restored and stopped, the canonical `mari-series.py`
now invokes the guarded retention collector for all four routes. Fresh plans must
pin `mari-series.py`, `storage_retention.py` and `retained_series.py`, along with
all other actual driver dependencies. The current working catalogs and pending
plans live in `runtime/storage-retention/policy.json`; new registered generations
replace obsolete ones only after successful completion. Superseded registered
compressed catalog caches are evicted; metadata and required catalog parents
remain. New tests use disposable temporary project roots, so fixture builds do
not accumulate in the canonical project. Derivative parents,
positive controls and queue package checkpoints remain dependencies even if older.
Unknown new artifacts are not disposable merely because no receipt mentions them.

Verified closed installer backup/package caches are evicted while screenshots,
original recipe metadata, restoration proofs and unclassified files remain.
Never select live metadata or a run still named by `active.json`. Historical
`deduplicate-closed-archive.py` receipts remain evidence; their keeper paths are
protected for compatibility. Identical immutable retained native outputs and ZIPs
may share storage, so all future edits/fault injections must use new revisions.
Run `python3 -B tools/visual-qa/test_storage_retention.py` after changes.
Regression: every route must complete its worker and restore before real cache
unlinking; open/changed files reject the whole preflight; a second publication
failure preserves artifact bytes, records the partial boundary and blocks retry.
The integration test replaces the game worker and OS open-file inventory, while
executing the actual series driver, hashing, gzip, retention and file operations.
No storage test establishes game rendering or translation correctness.

Thai series06 acknowledged its load key, then timed out while Scene_Map existed
but sceneStarted remained false. Passive diagnostics showed34 pending images,
then one, then none; the failure frame still showed the darkened save-list/loading
indicator. The original90s route limit expired before map readiness, with no
engine error. The game was stopped and Russian resources/protected files restored.
Fresh series07 retains the exact map/player/control guards and permits240s for
this shared first-save loading boundary. Timeout errors now preserve readiness,
pending asset details and observer age instead of only reporting None. Successful
native continuation is still required; a longer timeout alone proves no repair.

Thai series07 reached Continue with its first bridge request inactive before/after,
then the next native focus guard refused foreground input. No select-load request
was dispatched; the game stopped and resources/protected files were restored.
The exact failing focus sample was not preserved by that old recipe, so activation
cause remains unknown. New bridge receipts save native focus before evaluating
each guard, including rejection before request submission and after release.
Never infer a rejected first guard sent a key or that DOM focus proves native
background state. Preserve the owner's answer about intentional activation.

The owner confirmed series07's foreground appearance was spontaneous. The exact
activation cause is unknown; suppressing only browser window.focus was insufficient.
Fresh recipes now start the native window with temporary manifest show=false and
compose background-window-adapter.js before engine plugins. It suppresses native
NW window focus/show requests and retains lifecycle-event evidence. No game or OS
focus query is spoofed. test_background_window.cjs replaces NW.js with a fixture;
its passing policy checks do not establish native behavior.

The actual hidden-window proof is run-th-hidden-01. Native WindowServer metadata
omitted the onscreen flag while Oculix recognized the changing title/save/map/menu
frames. Full equipment capture and visual review passed at1280x960, with12 guarded
DOM pulses and final native focus inactive. There were no native focus/show events.
The original native capture path is unchanged; no browser image or canvas substitute
was used. This proves this run's hidden capture, not the cause of earlier activation.
Series08 dispatched only after this proof was restored. It later stopped on the
Vietnamese graphics wait described below. Never resubmit that exited series;
use the current checkpoint to find the active immutable run.

Vietnamese series08 never reached the title and sent no input. Observers stopped
while an input image remained incomplete. Native parent sampling captured
AppleMetalOpenGLRenderer flushContext -> Metal submitCommandBuffers -> IOGPU kernel
submission wait; the renderer sample was waiting in native IPC. The title guard
rejected the loading frame, then game/resources/protected files were restored.
The archive watcher consolidated the closed backup objects and exited on failure.

The successful isolated probe run-vi-hidden-gpu-01 removed only --in-process-gpu from
the temporary background manifest, leaving the same hardware WebGL path and all
other rendering flags. launch-settings.json retains the exact temporary settings;
gpu-process-proof.json records the actual owned separate GPU child. Runtime evidence
now reports renderer type/name and WebGL presence by passive field reads. The full native Vietnamese route and visual review passed with WebGLRenderer
type1, all12 requests/final native focus inactive, and verified restoration.
This is evidence for that changed run, not proof that all native driver hangs are
fixed. series09 applies the same recipe to15 remaining locales, with independent
focus/rendering/review/restoration gates for each.
Do not relaunch the exited series08 or overwrite any immutable snapshots.

Ukrainian series09 rendered the same last-menu-item clipping as Turkish, so its
frame was rejected and moved outside the final directory after verified cleanup.
The Turkish full/native positive control supports source-bound UI-prefix repairs
for13 remaining packages. Preflight of all14 stopped at Hindi's historical
arabic_runs.js pin; the first error did not identify a locale. A later per-locale
preflight isolated Hindi and confirmed the other parents. Arabic's actual source
pin matches current code. Do not label that original error as an Arabic failure.

The strict derivative verifier is unchanged. Hindi retains its existing selected
QA catalog and native package; no dependency guard is bypassed and no wording or
font asset changes. New payload overrides exclude Hindi; its future native visual
review still decides whether its menu needs repair. Full/current UI derivatives
remain technical candidates until their own real native frames are reviewed.

The13 strict layout derivatives and Turkish full control passed payload preparation
in payload-menu-ui-20261018-02:27 locale rows,7732 delivered files. The derived
selected QA catalogs retain those exact rows and all27 mandatory locale IDs.
Series10 uses these13 packages plus the unchanged Hindi QA catalog for the14
remaining captures. Do not run series09 again; its Ukrainian visual rejection
and restoration are complete. status.json is the current execution checkpoint.

Series10's first Ukrainian launch stalled before either observer, with no input.
The read-only native focus query also stalled. The worker received a documented
SIGINT; three exact recorded game survivors required SIGKILL after normal cleanup
exceeded30 real seconds. Their exit and Russian363-resource/8-file restoration
were then verified. Memory-pressure diagnostics did not indicate critical shortage.
The closed-run archive watcher reconciles its own duplicate objects, then exits.

The old startup/stop limits counted iterations containing potentially slow ps
queries. Current runtime uses a monotonic180s startup deadline (a verified cold start
previously needed128s) and30s stop deadline; each ps
query has its own10s bound. test_runtime_deadlines.py replaces process enumeration,
signals and the clock: a slow process query cannot stretch the stop loop to150
iterations, a matching successful close passes, and query timeout never means no
processes. Native process exit/restoration is separately required.

run-uk-hidden-default-gpu-01 removes the explicit legacy GPU buffer/rasterization/
worker-context overrides from the temporary manifest, retaining native WebGL and
hidden-window capture. Early startup diagnostics now run before the NW window
policy, whose atomic before-native-window-get/installed receipt identifies that
specific initialization boundary without bypassing it. The policy fixture also
checks phase evidence. This is a changed native probe, not a proven universal
GPU repair or evidence that the earlier missing observer was a JavaScript bug.

The Ukrainian minimum-size MenuCommand failure was not a driver error. The old
shared fitter still measured wider than82px at its18px floor, then threw the
multi-part file-row overflow error. Menu captions now permit Bitmap's native
horizontal width fitting at that floor; save rows and quest-label overflow guards
remain strict. The regression uses the actual НАЛАШТУВАННЯ caption for LTR and an
RTL ink-overhang fixture, verifies full text/bounds/font restoration, and keeps
matching short-label and multi-part negative controls.

The bridge originally released on Input.update errors only. A later scene error
can stop updates after three samples, before the fourth release tick. It now
releases and records the original error through SceneManager.catchException,
then delegates unchanged. The regression checks that exact post-third-sample
failure, original handler result, key release and no replay.

The full UK menu02 build changes only Bootstrap among288 resources; font/text/
config/binding inputs are identical. run-uk-hidden-default-gpu-02 passed actual
native review with the complete caption, all12 inputs/final native focus inactive,
and verified restoration. Its unaffected stats and weapon-text pixels exactly
match the preserved rejected reference. uk-full-native-control.json is the current
UI source control. Twelve fresh menu02 derivatives use it; earlier menu01 artifacts
are superseded technical candidates, not accepted evidence. Hindi's unchanged
package separately passed run-hi-hidden-default-gpu-01 native review, including
conjuncts and below-baseline marks; no historical source guard was bypassed.

The first seven fourth-frame native-key runs retain84 successful engine
acknowledgements, native focus checks and after-release states, but their legacy
Python producer overwrote the numeric subprocess exit code in the final JSON.
Do not fill historical receipts with inferred zeros. The final verifier accepts
that documented legacy success format and reports result-code retention counts;
DOM-bridge status codes are separate from native subprocess exit codes. Future
native receipts now preserve the actual process returncode in the final write.
The current series uses immutable DOM-bridge snapshots, so this metadata-only
producer correction does not alter its live dependencies or input method.

The Arabic series11 equipment transition stalled with two unchanged native atlas
images in `decrypting` state. The temporary equipment-assets.js fixture now records
passive XHR events for those exact atlas URLs and reserves the two real native
ImageManager bitmaps after the first save is ready, before X. It neither replaces
request callbacks nor marks images loaded. Any accepted capture using this fixture
is a reserved-cache test, not evidence of correct cold equipment loading. Its
regression proves bounded paths, native API delegation, decoded-image readiness
and unchanged map state; native capture and review remain separate gates.

run-ar-prefetch-01 stopped during startup on a10s ps timeout, before its observer.
It closed normally and restored363 resources/eight protected files; no image was
accepted. Startup now tolerates a transient unavailable process query inside the
same180s deadline, records the timeout and retains the same launch. Persistent
query failure still throws; positive evidence of game exit fails immediately.
The actual wait helper has regression controls for all four outcomes. Process
queries outside this startup observer wait retain their strict failure behavior.

run-ar-prefetch-02 reached the real equipment scene with both atlases decoded;
XHR traces show200, complete response sizes and installed onload handlers at
completion in this cache condition. This does not diagnose the earlier on-demand
stall. Its frame was visually rejected: Arabic item-help ink was clipped. The
rejected PNG is preserved in the closed run, not the upload directory. Series12 used unchanged packaged UI bytes for the remaining LTR locales. Five
were accepted/restored; Greek later stopped at the native capture boundary.
The separate RTL full/native control passed as recorded below.

The item-help repair in ui_layout.js applies only to RTL Window_OmoMenuHelp.
Native rich text is rendered unchanged on a detached padded bitmap with the real
description width, then its complete measured ink is copied unscaled beside the
native icon column. Original width overrides, contents and renderer errors are
preserved; measurement calls and all LTR paths delegate unchanged. The regression
models advance/ink divergence, two lines, mixed Latin/numbers, rich-text arguments,
own/inherited width restoration, native failure and empty/clipped/oversized ink.
Those fake-renderer controls do not establish actual Canvas/font correctness;
the full Arabic build and native visual control are required separately. Both passed in run-ar-item-help-01: both description lines are complete beside the icon; unaffected stats and weapon-heading pixels match the rejected frame exactly. The control receipt is diagnostics/native-artifacts-20261018-help-01/ar-full-native-control.json.

Series12 dispatch was held at its verified coordinator PID56808 while Filipino
finished/restored, then the separate Arabic full/native control ran. The same
coordinator resumed after Arabic restoration; no replacement batch was submitted.
The exact SIGSTOP/SIGCONT identity and timing are in series-12/dispatch-hold.json.

Series12 Greek loaded the first save normally, then screencapture returned1
with exactly `could not create image from window` before X. Its diagnostic
capture immediately succeeded and showed the correct unobstructed map; normal
closure and363-resource/eight-file restoration were verified. No Greek final
image was accepted. Vision now re-enumerates the owned native window and retries
that exact image-read error once, with a separate raw path and per-attempt JSON.
It never repeats game input. Other errors and persistent failure stop immediately;
capture timeout is10s. test_native_capture.py replaces native metadata/capture
APIs and checks success, bounded recovery, fresh window identity, unique raw paths,
permission-error rejection and ambiguous-owner rejection. Actual native capture
is a separate gate. Series14 pins fresh recipes for the final6 locales; the
unsubmitted series13 snapshots remain preserved and are not dispatched.

Item-help neighboring-data checks must apply the native YEP MessageCore line-break
contract before counting lines. In non-WordWrap mode, BR tags are removed and raw
newlines remain; in WordWrap mode raw newlines are replaced before BR conversion.
Regression: MOOD WRECKER (skill77) contains `line1\n<br>line2`, which is two native
lines, not three. The12 Arabic/Persian/Hebrew Weapons/Armors/Items/Skills resource
sets all contain no WordWrap entries and at most two native explicit lines;
diagnostics/native-artifacts-20261018-help-01/description-line-boundary.json binds
the inputs. This does not establish glyph-width fit or full inventory runtime
coverage. The three actual native knife frames remain the visual control.

Equipment QA completion:108 native PNGs (4 per27 locales),27 reviewed fourth
frames and81 earlier PNGs unchanged. Final native validation and the official
site screenshot dry-run passed. The dry-run validated108 inputs and proposed108
additions/0 replacements/0 skips; nothing was applied. completion.json binds the
frozen native report, CLI execution receipt/log and post-encoding PNG hashes.

Finish by validating native evidence, running the official CLI dry-run once,
then checking the unchanged108 source hashes and every locale/order in its plan.
Write the completion receipt before the status pointer. These are separate atomic
file replacements, not one transaction: after interruption, verify the receipt
hashes and roll the status pointer forward. No asset rollback is involved.
The legacy Russian observer omits ConfigManager.language; require the exact
verified repaired-Russian archive and installed-file hashes plus native Russian
review instead of inventing that missing measurement. Other locales retain the
direct runtime language/locale assertions. The project has no Git repository, so
code changes are canonical local files but could not be committed.

## Fifth frame: Joker Jash vertical wave

The October18 06:50:54 reference video ends at playground event18 (24,28),
`dreamworld_npc_dialogue_playground.message_30`. Load first save and approach from
(23,28) facing right with the followers in a horizontal row. The saved box is
already open (page4): close it, guard page3 and map readiness, then reopen the
original jack-in-the-box event and wait for its complete dialogue. The source uses two size increases and `SINV[1]`. Do not
replace it with a static re-render, alter translation strings, or capture a
partially revealed message. Keep the previous108 PNGs hash-bound and unchanged.

`wave_route.py` uses guarded bridge keys and the existing hidden native capture.
`wave-observer.js` only reads original TDS effect/sprite fields. Require complete
paused text, an active vertical effect, changing native sprite anchors, and
changed pixels in the native dialogue region across captured phases. Preserve
all phase frames and passive samples as animation evidence; only one original
native1280x960 PNG per locale belongs in the flat final directory, named
`<locale>-05-joker-jash-wave.png`. Every final image still requires visual review
for full text, visible wave deformation, glyphs, RTL, clipping and overlays.

Prepare immutable dependencies with `prepare-wave-run.py`, execute
`mari-session.py --route wave`, then issue the hash-bound visual gate through
`record-wave-review.py` only after inspecting actual pixels. `test_wave_route.py`
checks positive/negative runtime guards using synthetic fields; it does not
establish native font rendering or actual animation. Regression: a static,
horizontal, inactive or incomplete text effect must never pass as a complete
vertical-wave capture, even when the requested scene was reached.

The initial Russian proof retains before/after native frames for every movement.
Subsequent immutable wave recipes use fresh exact map/player coordinates as the
per-tile movement guard and retain every key, native-focus and semantic result;
they omit redundant intermediate map PNGs. Title/load recognition and final native
phase captures are unchanged. Prepared series01 is unsubmitted; series02 pins
this bounded diagnostic reduction without editing the live Russian snapshot.

The actual first-save event18 starts on page4 with its box already open.
One confirmation closes it and clears self-switchB (page3); the following
confirmation plays the crank/pop and displays message30. Guard that intermediate
page and map readiness explicitly instead of assuming the first key opens
message text. Russian run02 exposed the earlier one-key assumption and must
finish cleanup before retry. Approach ends with four rightward steps so the
followers match the reference's horizontal row; mirror event8 is inactive in
this save. Never change self-switches through a QA API to bypass the event.

Turkish series03 stopped after Continue while two original save-list portraits
remained in `decrypting` state. The bridge key was sampled/released; no final
frame was accepted and Russian resources/eight protected files were restored.
Fresh wave recipes add file-assets.js: reserve only the two exact native
ImageManager face bitmaps on the ready title screen, and require their real
native decoded-image dimensions before Continue. Passive XHR listeners retain
response status/sizes and callback-presence timing without replacing callbacks.
Native wave samples also retain this fixture and request evidence. These are
reserved-cache captures, not proof of correct cold save-list loading or its root
cause. test_file_assets.cjs replaces native image/XHR APIs and tests the bounds,
real API delegation, ready-state gate and callback/return preservation; the real
Turkish native control is required before applying the recipe to pending locales.

Arabic series04 reached the complete shaped dialogue but exposed one whole-run
sprite, so wave_ready correctly refused it. Do not lower the sprite/phase gate
to accept a flat block that merely bobs. The shared delivered run_wave.js repair
preserves full-run Canvas shaping and phases native texture strips across its
width. New contextual packages require full current compilation/readback, exact
unchanged text/font/config comparisons and their own actual native review.
Unchanged accepted languages need no recapture. Arabic cleanup restored all363
resource paths and8 protected files before any repaired launch.

A native capture timeout can occur after the complete1280x1016 window PNG has
already been written. Reconcile that unique output after subprocess.run has
terminated/waited its exact capture child: require PNG signature/size, complete
chunk verification and full pixel decoding. Preserve returncode=null and the
actual timedOut evidence; do not invent exit0. If output is absent, corrupt or
wrong-sized, re-enumerate the owned window and permit one bounded read only,
using a distinct raw path. Persistent failure and permission errors still stop;
no gameplay input is replayed. Native Arabic run01 preserved one such complete
file; the subsequent immediate diagnostic frame also succeeded. The mock tests
cover all recovery branches but do not establish a WindowServer root cause.

Wave pixel comparison excludes the native animated continue indicator below
Y890. Every previously accepted native phase was rechecked against the text-only
region (20,752)-(1258,890). A matching indicator-only negative control and
text-pixel positive control prevent a blinking pointer from proving text motion.
Spatial anchor variation is independently required, not just temporal movement.

After the fully imaged route proofs, current wave recipes keep Oculix/native
frames at Continue, select-Load, opening Jash and the final three phases. The
other load-slot/prompt/movement/close-box transitions retain fresh exact runtime
markers, protected-file checks, native-focus evidence, unique bridge acknowledgements
and semantic result JSON; redundant diagnostic images are omitted. This changes
capture overhead, not the required UI states, keys, save or final native evidence.
Prove this complete current path on isolated Czech before dispatching remaining
locales. It is a changed capture condition, not proof of the cause of earlier
startup or WindowServer failures.

Hungarian series07's final movement request received no reply within the old15s
wait. Its exact unique request was later acknowledged with all three normal
samples and released; the reply timestamp is42.976s after submission. The original
failed producer receipt remains unchanged, and late-input-reconciliation.json
records that separate outcome. Memory/disk checks did not indicate exhaustion;
the native process exited before sampling, so no native stack cause was established.

Current bridge producers wait up to60 monotonic seconds for that same request,
record actual monotonic wait/deadline, and never replay it. Exact ID, three held
samples, key release, focus and post-action semantic checks remain mandatory.
No image/scene/input is credited merely because the deadline increased. The
fake-clock test_bridge_deadline.py checks the recorded43s case, old15s failure,
wrong-ID rejection, pending limit and immediate-error handling without native
scheduler claims. A fresh Hungarian continuation must pass actual native capture,
review and restoration before dispatching the other pending locales.

Hungarian run-hu-wait-01 stopped before title readiness: the original title scene
was constructed but sceneStarted=false and cursor_menu.png remained decrypting.
The driver previously began native image queries merely on the constructor name,
while the title could not yet be valid. Current recipes also wait through that
known not-started title state before querying native windows. The original
deadline and final native marker/fresh-state requirements remain unchanged.
This reduces premature capture contention; it does not establish the stall cause.
Regression: a constructed not-started Title must issue no capture until ready;
a started Title must still pass native Oculix and freshness checks.

## Sixth frame: mailbox shop, Jacks selected

The 2026-10-18 11.28.22 owner video ends in Scene_OmoriItemShop, Buy mode,
third item78 Jacks at25 clams, owned0 and gold72. Map92 event24 is copied from
Map346 event265. Stand20,40 facing up; select Buy then move down twice without
confirming an item. Preserve all135 previously reviewed PNGs.

Map92 uses YED_Tiled; RPG Maker map.data contains zero tiles and cannot establish
passability. The passive shop observer records actual Game_Player.canPass edges
once the first-save map is started, controllable and has no running event.
The route uses a bounded BFS through that directed native grid to20,41, then
steps up to20,40. Every step still requires fresh exact before/after map position
and released unique input, never a teleport. An unavailable edge or unexpected
dialogue/choice stops the run. Complete representative native review is required
before batching. These state fixtures do not prove the real native route.

The observer records list index, actual item IDs/prices, fully rendered help,
shopkeeper image readiness and native shop windows. Reject a quantity or purchase
window, partial description, missing artwork or unexpected goods. Bind the final
inventory/gold to the loaded-save snapshot; no item confirmation is sent.
Final PNGs are named <locale>-06-mailbox-jacks.png and individually reviewed.
Any site-transfer validation remains subject to the prior outbound approval
rejection; creating the next screenshots does not authorize that transfer.

Spanish shop series01 stopped after talk-mailbox: the longer localized greeting
was initially typing, then automatically opened the native three-choice menu.
The old before-dialogue guard required pause=true after typing; choices instead
leave pause=false with textState=null, so it waited45s despite the expected panel.
No Buy input was dispatched. Current mailbox_interaction_ready waits for either
complete paused event24 dialogue or the active native choice panel, checks which
state actually appeared, and advances only that state. The fixture includes the
observed automatic transition, incomplete-text negative and wrong-event negative.
Preserve failed series01 and prove the changed recipe on Spanish before batching.

Shop draw diagnostic01 stopped before gameplay because the first runtime observer
file already existed but was stale while startup synchronously loaded resources.
The old observer wait asserted freshness immediately on file existence. Future
recipes retain the same process and original180s deadline until its genuine
fresh sample appears; identity, process-exit checks and per-action freshness
remain strict. test_runtime_deadlines.py includes stale-to-fresh and persistently
stale controls. Diagnostic01 restored363 resources and8 protected files; no input
or shop evidence was produced. Its immutable snapshot is preserved.

Spanish shop run-es-02 was initially visually rejected for missing prices/count.
Reopening its exact hash-matched PNG demonstrated all four prices and the full
owned count were already present: that human reading was wrong. No renderer fix
is warranted by that claim. The initial rejection and failed gate exit remain
archived; review-reconciliation.json binds the unchanged original pixels, original
failed producer status and superseding actual review. Final validation accepts
only this exact review-gate failure with verified correction plus every normal
artifact/input/restoration check; other failed producers cannot use the exception.
Regression: confirm a claimed missing field on the exact original pixels, with a
bounded crop if useful, before changing renderer/font code. Private draw probes
and later success do not prove an earlier image was wrong or establish causality.

Diagnostic03 reserved original mailbox/mailboxLegend images at title and reached
the shop. Native draw calls preserved prices and right-aligned ink inside bitmap
bounds; the diagnostic image visibly includes all prices/count. This is warm-cache
capture evidence, not proof of cold-loading repair. Diagnostic02 stopped with those
two native images still decrypting; no callbacks were replaced.

Thai sixth-frame native QA exposed a separate real help-layout overflow: full
logical text and glyphs existed, but only the speed-reduction line remained over
the item title with a continuation pointer. Native help has96px contents and
starts description atY24, leaving72px. The cluster adapter raises line height
toceil(fontSize*1.35); two28px lines need76px and native paging clears the first
line. Shared Thai shop fitting now measures explicit breaks and cluster wrapping
and selects a bounded fitting size during the existing native font reset. Other
windows and non-Thai text keep their original reset. Unknown oversized help
retains its native path; no exhaustive all-item readability claim is made.

The full Thai shop-help build changes only Bootstrap; all292 resources were
read back, with text/fonts/config/bindings and Install unchanged. The actual
run-th-help-01 native frame shows both full sentences, separate title and intact
marks at26px. Passive original-renderer proof records one page and pause=false.
Russian363 resource paths and8 protected files were restored. Preserve the old
rejected frame and bind reuse to thai-full-build-delta.json plus the new native
control. Regression: original two38px lines exceed the72px band; fitting two36px
lines must remain one native page, without hiding or rewriting either sentence.

An owner-reported Thai artifact concern reopens acceptance even when a prior
hash-bound visual review passed. Preserve that review and the native PNG; record
the hold in `20261018-sixth/thai-owner-review/status.json`. Diagnostic crops stay
outside the deliverable folder. The progress helper excludes the held locale,
and final validation rejects an unresolved hold. A prior automated or visual pass
cannot silently supersede newer owner feedback.

Arabic shop series07 stopped on the first item's help, before moving selection:
the active list and shopkeeper were ready, but the native message paused after
its first line. The contextual-run adapter's dialogue leading also expanded
compact shop help. Its scoped candidate retains native leading while
`WindowItemShopMessage._drawingItemText` is true; contextual shaping, text, font
size, other windows and ordinary shop dialogue remain unchanged. Arabic,
Persian and Hebrew share this renderer. Native proof is still required for each
delivered locale. Regression fixtures compare the exact compact shop scope with
the same window outside item drawing and a regular message carrying the flag;
only the actual compact scope may bypass dialogue leading. Fixtures replace
Canvas and do not establish glyph fit or native paging.

The owner confirmed the updated Thai frame looks fine; the hold's resolution
binds that confirmation to the exact PNG hash, which final validation rechecks.
Arabic run-ar-help-03 proves both selected-item help lines fit on one native
page at28px with pause=false. Its source-bound package delta changes only
Bootstrap, with all text, fonts and bindings unchanged.

Mailbox interaction readiness must guard both the initial talk transition and
the subsequent dialogue loop: either a complete paused event24 message or its
active choice panel is valid. Requiring a dialogue pause at only the initial
transition still races an automatically opened choice panel.

Navigation eligibility is separate from final screenshot eligibility. Greek
series09 reached the active second-item list but paused its long, unselected
help text. A fresh route may move through that active list without purchasing;
it must still require the final selected Jacks description to finish with
textState=null and pause=false. Fixtures prove the paused-help positive
navigation control and negative final-capture control separately.

Filipino series08 stopped before Continue with four original images remaining
decrypting, empty image sources and zero dimensions; saves were not loaded.
After restoration, the fresh instrumented series09 run recorded successful
native responses with handlers present and real decoded images, then passed
native review. This establishes the new capture's loading, not the first
attempt's root cause or a production cold-load repair. Shop observations now
retain passive request receipts for both save faces and both mailbox images.

Final native-content identity compares every RGBA byte against the raw window
crop `(0,56,1280,1016)`. An RGBA difference bounding box can inspect only alpha
and miss color changes when alpha is unchanged. Regression: the real positive
crop must match, while flipping one RGB channel in memory with unchanged alpha
must fail identity. Never modify delivered evidence to exercise this control.

Hindi series10 proves the same compact-help leading failure on the actual target:
item78 pauses with40px leading, so two lines exceed the72px band. The scoped
Devanagari correction preserves native leading only during item drawing, as in
the shared RTL adapter. Native run-hi-help-01 shows both complete lines at the
unchanged28px font, one native page with29px leading and pause=false. Compared
at the same1280x960 viewport, the title, counters and glyph shaping are retained.
The old failure frame remains in its run directory. All four new complex-script
packages have identical authored inputs, locale configuration, bindings and
font/text resources; only Bootstrap differs from their accepted wave builds.
