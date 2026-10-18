# OMORI shared CLI preparation

Objective: enable independent per-language standard text localization of OMORI Steam
build 8879120 through Codex CLI. Implement and verify the shared source/adapter prerequisites;
do not translate the game in this preparation assignment.

Canonical project: {{ROOT}}. Master: {{MASTER}}. Run: {{RUN}}.
Model: GPT-6.1 Sol, reasoning high. This is an explicitly authorized fresh CLI task;
no inherited transcript. Do not spawn agents, create chats, create goals, call translation
services or start another Codex process. Use English for instructions/docs/reports.

Read the applicable workstation AGENTS.md, master AGENTS.md and these required files fully:
/Users/antonkrutov/.codex/instructions/sitefor-mods.md
/Users/antonkrutov/.codex/instructions/game-localization-prompt.md
/Users/antonkrutov/.codex/instructions/game-localization-audit-workflow.md
Use vn-localization/vn-game-assets/vn-game-localize skills for the relevant technical work.
Read project LOCALIZATION_CHECKPOINT.md, glossary/process-binding.md,
SOURCE_RESEARCH.md and the relevant technical portions of TRANSLATION_AUTHORING.md.
Do not read historical chat transcripts or the full Russian translation by default.

Ownership: create/modify only {{ROOT}}/tools/multilingual,
{{ROOT}}/source/multilingual and {{ROOT}}/runtime/multilingual. Their existing checkpoints
are your resumable state. Other language/glossary work is live: do not write master,
glossary/, translation/ru, build/ru, dist/ru, original tools, original source, installed
game files or saves. The project intentionally has no Git: do not create a repository.
No game/installer launch, installation, textures, images/OCR, publication, push/deployment,
server lifecycle changes or new paid service. Read site content only through ./vnrevival.

Existing facts to VERIFY:
- Shared base source/text-corpus-8879120-02 has 20,775 stable IDs and typed exact-preservation
  contracts; 77 entries are explicit technical retentions, not translated words.
- source/native-yaml-8879120-01 recovers 19 visible YES/NO fields omitted by PyYAML.
  Native bundled js-yaml comparison covers 211 assets. The old complete inventory/editorial
  claim is invalidated. Do not start locale mass translation on that old acceptance.
- source/special-scenes-8879120.json and .md register 26 cases; registration is not exhaustive
  discovery or locale wording acceptance. Verify the current source discovery contract.
- The native direct-overlay delivery replaces OneLoader. Current Russian native05 provides
  evidence for bootstrap order, legacy NW.js function normalization, YES/NO choice parsing,
  save/load clipping and Bitmap+Sprite title row sizing. Reuse the responsible mechanisms
  and exact regression conditions; do not transfer Russian words or Russian acceptance.
- Sources are English; no Russian pivot or old deleted-project translations.
- Official en/zh/ja/ko are excluded; ru already exists. All other 26 site locales are targets;
  Serbian uses Cyrillic. The canonical 31-language catalog is master/lib/language-data/site-locales.ts.
- A separate active glossary chat owns current canonical source/target glossary revisions.
  Preparation must not duplicate or mutate its work.

Deliverables:
1. One complete SHARED new source inventory, preserving base stable IDs and adding the19
   native-YAML IDs exactly once, pinned to original assets/version/protected values. Confirm
   complete agreed text coverage and all affected extraction/no-op/reinsertion regressions,
   including native scalar typing. Use original source and verified evidence. Unknown coverage
   or a new missing asset blocks acceptance; do not set passed just because counts sum correctly.
2. A single explicit --locale tool binding for the fixed universal stages. Add common CLI
   tools in tools/multilingual; keep the old Russian recipes untouched. Tools accept explicit
   project root/data paths because this directory is frozen under {{RUN}}/tooling after you finish.
   Create bounded workset/source reads, glossary snapshot verification, locale batch validation
   and assembly/progress commands. No silent ru fallback, no translated logic/identifiers,
   and no algorithmically generated wording. Retain exact protected structure, span boundaries,
   display labels and encoded dialogue. Do not omit harder adapters from the source queue.
3. Versioned common process binding plus locale renderer/configuration matrix, with actual
   supported/blocked/unverified mechanisms and static commands. Runtime risk decision is
   {{RISK}}. Russian's former waiver alone does not establish Arabic/Indic/Thai rendering.
   No runtime launch is authorized in this task. Identify scripts requiring joining, bidi,
   reordering, marks or extra glyphs. A proven failed mechanism blocks dependent mass work
   even if the owner later accepts unverified runtime. Significant engine replacement needs
   owner agreement. Font cmap alone is not rendering proof.
4. tests exercising locale selection (including unknown/missing), shared source19 integration,
   protected-value rejection with matching positive controls, locale write isolation and
   actual delivered plaintext readback. Mark native boot/visual checks not-run. Do not weaken
   universal editorial acceptance; semantic/independent review belongs to later locale tasks.
5. source/multilingual/acceptance.json with `source` and `adapters` values `passed` ONLY when
   their evidence establishes those gates. Include inventory path/hash, exact counts, commands,
   evidence paths, renderer matrix and limitations. The supervisor requires `inventoryPath`
   (project-relative JSON unit array inside source/multilingual), `inventorySha256`, and
   nonempty `evidence` array of {"path": project-relative-file, "sha256": raw-file-hash}.
   Preserve ALL original base/supplement record fields exactly; supplementary metadata may be
   additive. Duplicate, missing, extra or changed source records fail the supervisor gate.
   Missing later fonts/packages do not imply
   complete local delivery. tools/multilingual/PROCESS.md must tell locale workers exact commands
   for all stages and how to resume, author special-scene decisions first, preserve controls,
   and report unmet gates. Include prerequisite checks for target glossary against the CURRENT
   canonical English revision; old accepted definitions may need dependency reconciliation.

Pinned old helper reference copies are {{RUN}}/snapshot/reference-tools. They are disposable
implementation evidence, not a second checkout; absolute root assumptions in them must be
handled explicitly. Before relying on existing source/helper evidence compare hashes and
actual affected boundaries. Check inexpensive prerequisites before full validation.

Continue until shared preparation is verified or concretely blocked. Save CHECKPOINT.md
under source/multilingual. If a substantive unit is complete but more authorized work remains,
return status=continue with actual artifact evidence; the deterministic CLI will open a fresh
session from the checkpoint. Do not stop merely after a plan or count. On genuine blocker return
blocked and exact next action. Return prepared only with actual shared source/adapter acceptance.
