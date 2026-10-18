# Implement finite editorial acceptance and progress gates for OMORI CLI

Owner explicitly authorized repairing the CLI queue, finishing ready localizations and
automatically starting following languages. You are one fresh no-history GPT-6.1 Sol/high
CLI engineering job within the total six-job limit. No agents/chats/extra model calls.
Canonical no-Git root: /Users/antonkrutov/Desktop/omori full translation mod.
Read mandatory sitefor-mods.md, game-localization-prompt.md and
game-localization-audit-workflow.md in /Users/antonkrutov/.codex/instructions.
Use English for operational files. No publication/deployment, server lifecycle, game/
installer launch, installed-game/save changes, source inventory or Russian modifications.
Canonical master/glossary content is read-only, separately owned. No text generation.

WRITE ONLY tools/localization_acceptance.py, tools/test_localization_acceptance.py,
and runtime/multilingual/shared-acceptance/. Coordinator owns localization_cli.py,
localization_pipeline.py, templates and docs. Another engineer owns tools/multilingual/
delivery/. Never edit the frozen executing run snapshots or locale author inputs.

Implement reusable machine gates to replace the bug that ANY changed report/checkpoint
counts as progress. Five complete drafts and their real full/partial editorial reads exist
under translation/{es,es-419,pt-BR,de,fr}; preserve and reuse valid evidence. Other locales
need ordinary translation. Do not invent acceptance or run full automatic semantic reads.

Implement these callable interfaces; save exact CONTRACT.json immediately if clarification
is needed, but prefer this interface:

inspect_locale(root: Path, locale: str) -> dict
  explicit locale validation against existing26 configs; load pinned canonical inventory
  source/multilingual/shared-8879120-03/units.json; validate all batches' locale/source/hash,
  unique exact IDs/sources, immediateEdit flags and authored controls via frozen/current
  direct-authoring mechanisms. Return inventorySha256, glossarySha256, corpusSha256
  (canonical ordered JSON id/source/target objects compact UTF8), authoredVisible,
  totalVisible, missingIds, corpus (complete rows) and any concrete errors. The77 technical
  retentions stay separate; visible denominator20717, total20794. Do not silently exclude
  Turkish's1219 local classification findings or forge their wording.

progress_snapshot(root, locale) -> JSON-serializable dict
  Compact semantic progress derived from actual authored text and validated stage receipts,
  not mtime, file count, checkpoint bytes, claims or raw closure-size growth alone.

validate_receipt(root, locale, role, receipt_path, task, session_id) -> dict
  task has id, role and input bindings from inspect_locale, plus previous progress.
  Every job writes an immutable receipt beneath translation/LOCALE/pipeline/tasks/ID/.
  Receipt fields: schemaVersion=2, taskId, locale, role, disposition
  (continue/stage-complete/blocked), inputBindings (inventorySha256,glossarySha256,
  corpusSha256), summary, blockers array, evidence array (path,sha256), and work.
  Unambiguous role-specific work schema is yours to define, document CONTRACT.json and
  include valid minimal examples. Coordinator will use your contract in prompts.

Roles and gate semantics:
- author: only actual newly authored visible IDs/control-safe repairs count as progress;
  stage-complete requires zero canonical missing visible IDs plus structural validation.
- editor: reconcile/import valid prior actual full source-to-target review evidence; verify
  exact source/target hashes and actual read-ID lists/decisions and their source artifacts.
  Do not fabricate coverage by enumerating the corpus or copying a clean flag. Do not
  require rereading the whole corpus merely because operational receipts/schema changed.
  One full semantic pass, consolidate objective findings, apply admissible corrections,
  complete minimal dependency closure and mandatory regressions following universal audit.
  Record per-ID reviewed pair hashes, actual evidence references, resolved finite work
  items and real finding dispositions. Missing current-source glossary compatibility is
  a separately recorded prerequisite; close it using owner-authored glossary receipts/
  compact-source comparison locally, not canonical edits or blind re-pinning. This role
  can prepare local compatibility evidence/two required review layers directly when old
  evidence is inapplicable. Existing glossary owner files are read-only.
  Stage-complete means the editor's finite work is handed to a distinct independent
  reviewer; it does NOT mean accepted localization or ready release. Concrete external
  blockers stop only affected work; no repeated unchanged self-reads.
- reviewer: distinct fresh CLI session, no authored text edits; complete closure/delta
  source/target read with identifiable independent session and exact pair hashes.
  Findings are exhaustive objective proposals. No self-review or validator-only credit.
  Corrections return to editor once as a consolidated batch; next reviewer gets corrected
  IDs + current-minus-previous closure + explicitly invalidated evidence, not full restart.
  Baseline reviewed unaffected rows stay valid. Repeated unrelated findings trigger one
  consolidated remedial review, not unbounded one-error cycles.
- resources/package: validate actual helper build/package verification receipts; native
  adapter currently being implemented separately. Do not auto-accept a ZIP path or plaintext
  sidecar as playable delivery. These may use shared adapter's documented verify entry.

validate_receipt returns JSON-compatible dict with roleComplete, meaningfulProgress,
nextRole, progress, and blockers, plus validated saved evidence references. It must reject
report-only continue; incomplete role-complete claims; stale inputs; cross-locale/symlink
escapes; fake full coverage; same-session independent review; changed/unread closure rows;
and unknown external stages. No generic stage name may turn requirements into passed.

completion(root,locale) -> dict
  Validate recorded editorial acceptance/full semantic coverage + clean independent
  closure/delta + current glossary compatibility + protected-resource/native archive
  verification. Return ready=False and exact remaining gates until actual evidence passes.
  Runtime/visual remain explicitly not-run under owner accepted-static decision, never
  marked passed. Publication and game installation are outside scope and not prerequisites
  for local static delivery. Text-bearing-image requirements remain explicit, not faked.

Current source SHA256:4faf2a7b0bc682febcbcb03fe67ea7c2cad1ead21723ba5ae47c6f33d265214d.
Frozen authoring helpers: runtime/cli-localization/runs/20261014T124749Z-facf4e91/tooling-direct-v2.
Legacy real evidence examples: de/editorial/semantic-01/review-input-rows.json and its reading
notes; fr/editorial current CHECKPOINT; es/audits/semantic-01; es-419/editorial/cycle0006
(resolve actual paths from checkpoint); glossary/*/acceptance.json points to old source
11d48..., current compact English e839... and reference d63c... . Do not print whole glossaries
or historical chat logs; inspect bounded schemas, then exact needed fields.

Add meaningful positive/negative unit tests and actual read-only inspect_locale on existing
es/de data. Save implementation and contract; finish instead of only producing a plan.
Preserve original scripts/inputs; no new parallel status tracker, use existing queue state
and per-locale pipeline receipts as its evidence. Return local-scope-complete for implemented
verified helpers, continue only with concrete code progress, blocked for exact obstacle.
