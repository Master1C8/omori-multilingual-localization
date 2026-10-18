"""Machine-gate regressions; synthetic wording is fixture data, never game translation.

Miniature inspect tests replace only the frozen engine-control subprocess (its
real boundary is exercised by the separately saved real es/de inspections).
Receipt, path, hash, read, closure, glossary and replay gates run without mocks.
Native adapter tests replace its expensive subprocess and explicitly test the
binding/result contract; they do not establish actual native payload correctness.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import localization_acceptance as gate


class AcceptanceTests(unittest.TestCase):
    def test_owner_checkpoint_reuse_never_runs_native_subprocess_and_tamper_fails_closed(self):
        manifest = self.write('build/multilingual-delivery/de/revision/manifest.json', {'siteLocale':'de','files':[{'path':'fixture','sha256':'payload'}]})
        accepted = self.write('build/multilingual-delivery/de/revision/ACCEPTANCE.json', {'siteLocale':'de','status':'passed-technical-candidate','manifestSha256':manifest['sha256']})
        self.write('tools/multilingual/delivery/native_delivery.py', {})
        run=self.root/'runtime/cli-localization/runs/checkpoint-test'
        self.write('runtime/cli-localization/current.json',{'run':str(run)})
        decision=self.write('runtime/cli-localization/runs/checkpoint-test/owner.json',{'authority':'owner','instruction':'Reuse unchanged native checkpoints; remove repeat checks.','reuseVerifiedNativeCheckpoints':True,'locales':['de']})
        self.write('runtime/cli-localization/runs/checkpoint-test/config.json',{'nativeCheckpointDecision':decision})
        self.write('runtime/cli-localization/runs/checkpoint-test/state.json',{'locales':{'de':{'workflow':{}}}})
        actual={'status':'passed-technical-candidate','siteLocale':'de','authoredEntries':3,'files':1,'mappedTargets':0,'archive':None}
        with patch('native_checkpoint.verify_checkpoint',return_value=actual) as reuse, patch.object(gate.subprocess,'run',side_effect=AssertionError('Repeated native subprocess')):
            record=self.create('resources',{'verification':accepted,'buildManifest':manifest},[accepted,manifest],'stage-complete')
            result=self.validate(record);self.assertTrue(result['roleComplete'],result['blockers']);reuse.assert_called()
            (run/'owner.json').write_text('{}')
            result=self.validate(record);self.assertFalse(result['roleComplete']);self.assertIn('decision changed',result['blockers'][0])

    def test_owner_media_exclusion_is_explicit_and_does_not_pass_missing_text_gates(self):
        run = self.root / 'runtime/cli-localization/runs/scope-test'
        self.write('runtime/cli-localization/current.json', {'run': str(run)})
        self.write('runtime/cli-localization/runs/scope-test/config.json', {})
        before = gate.completion(self.root, 'de')
        self.assertIn('imageTextInventoryAndPlans', before['remainingGates'])
        ref = self.write('runtime/cli-localization/runs/scope-test/media-scope.json', {
            'authority': 'owner', 'instruction': 'Exclude images and movies from the requested mod.',
            'locales': ['de'], 'images': False, 'movies': False})
        self.write('runtime/cli-localization/runs/scope-test/config.json', {'mediaScopeDecision': ref})
        after = gate.completion(self.root, 'de')
        self.assertFalse(after['ready'])
        self.assertIn('fullSemanticCoverage', after['remainingGates'])
        self.assertIn('independentClosureAndRegressions', after['remainingGates'])
        self.assertNotIn('imageTextInventoryAndPlans', after['gates'])
        self.assertEqual(after['applicability']['imageTextInventoryAndPlans']['status'], 'not-applicable-owner-excluded')
        self.assertEqual(before['gates']['visibleCorpus'], after['gates']['visibleCorpus'])
        path = run / 'media-scope.json'
        path.write_text(path.read_text() + ' ')
        rejected = gate.completion(self.root, 'de')
        self.assertIn('ownerScopeBinding', rejected['remainingGates'])
        self.assertIn('imageTextInventoryAndPlans', rejected['gates'])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='omori-acceptance-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.sequence = 0
        self.units = [dict(id=id_, source='source-' + id_, asset='test', role='visible') for id_ in ('a', 'b', 'c')]
        self.units.append(dict(id='technical', source='EXACT', asset='test', role='technical'))
        self.write(gate.INVENTORY, self.units)
        self.write('source/multilingual/shared-8879120-03/technical-retentions.json', [self.units[-1]])
        codes = ['es', 'es-419', 'pt-BR', 'de', 'fr', 'tr', 'zh-TW', 'pl', 'it', 'th', 'vi', 'id', 'uk', 'ar', 'cs', 'hu', 'nl', 'fa', 'ro', 'hi', 'fil', 'el', 'bg', 'sr', 'sw', 'he']
        self.write('tools/multilingual/renderer-matrix.json', {'locales': [{'siteLocale': x} for x in codes]})
        self.source = [{'id': 'concept', 'term': 'SOURCE', 'meaning': 'A bounded fixture concept.'}]
        self.master = self.root / 'master-source.json'
        self.write('master-source.json', self.source)
        self.write('source/current-glossary.json', self.source)
        self.glossary = {'siteLocale': 'de', 'sourceLocale': 'en', 'sourcePath': str(self.master),
                         'sourceRawSha256': gate._digest(self.master), 'source': self.source,
                         'target': {'concept': {'term': 'TARGET', 'meaning': 'A fixture target concept.'}}}
        self.write('translation/de/glossary-snapshot.json', self.glossary)
        self.write('glossary-translations.json', {'de': self.glossary['target']})
        self.write('source/special-scenes-8879120.json', {'cases': [{'id': 'CASE', 'unitIds': ['a']}]})
        self.write(gate.MEDIA_MANIFEST, {'assets': [{'asset': 'one.png', 'rawSha256': 'image-source'}]})
        self.media_sha = gate._digest(self.root / gate.MEDIA_MANIFEST)
        for key, value in [('INVENTORY_SHA256', gate._digest(self.root / gate.INVENTORY)),
                           ('TOTAL_VISIBLE', 3), ('TOTAL_OCCURRENCES', 4), ('RETENTIONS', 1),
                           ('MASTER_SOURCE', self.master), ('MEDIA_SHA256', self.media_sha)]:
            context = patch.object(gate, key, value)
            context.start(); self.addCleanup(context.stop)
        context = patch.object(gate, '_validate_controls')
        context.start(); self.addCleanup(context.stop)
        self.batch = {'siteLocale': 'de', 'sourceLocale': 'en', 'inventorySha256': gate.INVENTORY_SHA256,
                      'entries': [{'id': u['id'], 'source': u['source'], 'target': 'target-' + u['id'], 'immediateEdit': True} for u in self.units[:-1]]}
        self.save_batch()

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        return self.ref(name)

    def ref(self, name):
        return gate._ref(self.root, name)

    def save_batch(self):
        self.write('translation/de/batches/one.json', self.batch)

    def inspect(self):
        return gate.inspect_locale(self.root, 'de')

    def progress(self):
        return gate.progress_snapshot(self.root, 'de')

    def create(self, role, work, evidence, disposition='continue', session=None, previous=None):
        self.sequence += 1
        id_ = f'task-{self.sequence:04d}'
        previous = previous if previous is not None else self.progress()
        session = session or ('reader' if role == 'reviewer' else 'editor')
        task = {'id': id_, 'role': role, 'sequence': self.sequence, 'sessionId': session,
                'inputBindings': {k: previous[k] for k in gate.BINDINGS}, 'previousProgress': previous}
        doc = {'schemaVersion': 2, 'taskId': id_, 'locale': 'de', 'role': role, 'sessionId': session,
               'disposition': disposition, 'inputBindings': task['inputBindings'], 'outputBindings': gate._bindings(self.inspect()),
               'summary': 'Concrete bounded fixture work.', 'blockers': [], 'work': work,
               'evidence': list({r['path']: r for r in evidence}.values())}
        base = f'translation/de/pipeline/tasks/{id_}'
        self.write(base + '/task.json', task)
        self.write(base + '/receipt.json', doc)
        return task, self.root / base / 'receipt.json', doc

    def validate(self, record):
        task, path, _ = record
        return gate.validate_receipt(self.root, 'de', task['role'], path, task, task['sessionId'])

    def bundle(self, ids, session='editor', kind='semantic', finding_ids=()):
        corpus = {r['id']: r for r in self.inspect()['corpus']}
        rows = [{**corpus[id_], 'sourceSha256': gate._sha(corpus[id_]['source'].encode()),
                 'targetSha256': gate._sha(corpus[id_]['target'].encode())} for id_ in ids]
        base = f'translation/de/pipeline/fixtures/{session}-{kind}-{self.sequence}-{len(list((self.root / "translation/de/pipeline").glob("fixtures/*")))}'
        rows_ref = self.write(base + '-rows.json', rows)
        ids_ref = self.write(base + '-ids.json', ids)
        decisions = [{'ids': [id_], 'decision': 'finding' if id_ in finding_ids else 'clean',
                      'reason': 'Read the exact fixture source/target pair.', 'sourceArtifact': rows_ref} for id_ in ids]
        dec_ref = self.write(base + '-decisions.json', decisions)
        return {'kind': kind, 'sessionId': session, 'rows': rows_ref, 'ids': ids_ref, 'decisions': dec_ref}, [rows_ref, ids_ref, dec_ref]

    def glossary_work(self):
        evidence = []
        owner = self.write('glossary/de/acceptance.json', {'accepted': True, 'locale': 'de', 'sourceRawSha256': 'old-source'})
        layers = []
        for i in (1, 2):
            layers.append(self.write(f'translation/de/pipeline/glossary-layer-{i}.json', {
                'dimensions': ['fidelity', 'native-language'], 'reviewer': f'actual-reader-layer-{i}',
                'actualReadIds': ['concept'],
                'rows': [{'id': 'concept', 'source': {k: self.source[0][k] for k in ('term', 'meaning')}, 'target': self.glossary['target']['concept']}],
                'decisions': [{'id': 'concept', 'decision': 'clean', 'reason': f'Actual layer {i} fixture comparison.'}]}))
        current = self.ref('source/current-glossary.json')
        ref = self.write('translation/de/pipeline/compatibility.json', {'schemaVersion': 2,
            'snapshotSha256': self.inspect()['glossarySha256'], 'currentSource': current, 'ownerAcceptance': owner, 'layers': layers})
        return ref, [ref, current, owner, *layers]

    def closure(self, ids=('a',), changed=(), invalidated=(), previous=None):
        corpus = {r['id']: r for r in self.inspect()['corpus']}
        prefix = f'translation/de/pipeline/closures/{self.sequence}-{len(list((self.root / "translation/de/pipeline").glob("closures/*")))}'
        rows_ref = self.write(prefix + '-rows.json', [corpus[id_] for id_ in ids])
        catalog = [{'id': name, 'unitIds': ['a'], 'reason': 'Concrete fixture regression surface.'} for name in [*gate.MANDATORY_SURFACES, 'CASE']]
        catalog_ref = self.write(prefix + '-catalog.json', catalog)
        technical_ref = self.write(prefix + '-technical.json', [self.units[-1]])
        seeds = [id_ for id_ in corpus if id_ in set(changed) | set(invalidated)]
        evidence_ref = self.write(prefix + '-topology.json', {'fixtureConsumer': list(ids)})
        extra = [id_ for id_ in ids if id_ not in set(seeds) | {'a'}]
        dependencies = [{'from': 'a', 'to': extra, 'component': 'runtimeBindings', 'reason': 'Shared fixture consumer.', 'evidence': evidence_ref}] if extra else []
        recipe_ref = self.write(prefix + '-recipe.json', {'schemaVersion': 2, 'inventorySha256': gate.INVENTORY_SHA256,
                                                        'seedIds': seeds, 'dependencies': dependencies})
        registry = self.ref('source/special-scenes-8879120.json')
        doc = {'schemaVersion': 2, 'inputBindings': gate._bindings(self.inspect()), 'ids': list(ids),
               'changedIds': list(changed), 'invalidatedIds': list(invalidated), 'previous': previous,
               'components': {'context': seeds, 'repetitions': [], 'glossaryReferents': [], 'runtimeBindings': extra, 'regressions': ['a']},
               'recipe': recipe_ref, 'rows': rows_ref, 'regressionCatalog': catalog_ref,
               'specialSceneRegistry': registry, 'technicalContext': technical_ref}
        ref = self.write(prefix + '-closure.json', doc)
        return ref, [ref, rows_ref, catalog_ref, technical_ref, evidence_ref, recipe_ref, registry, *([previous] if previous else [])]

    def editor(self, ids=('a', 'b', 'c'), previous_closure=None, changed=(), closure_ids=('a',), invalidated=()):
        bundle, evidence = self.bundle(list(ids))
        glossary, more = self.glossary_work(); evidence += more
        closure, more = self.closure(closure_ids, changed, invalidated, previous_closure); evidence += more
        record = self.create('editor', {'reads': [bundle], 'glossaryCompatibility': glossary, 'closure': closure}, evidence, 'stage-complete')
        result = self.validate(record)
        self.assertTrue(result['roleComplete'], result['blockers'])
        self.assertEqual(result['nextRole'], 'reviewer')
        return record, closure, evidence

    def reviewer(self, editor, closure_ref, closure_evidence, ids=('a',), session='reader', finding_ids=()):
        bundle, evidence = self.bundle(list(ids), session, 'closure', finding_ids)
        handoff = self.ref(str(editor[1].relative_to(self.root)))
        closure = gate._json(self.root / closure_ref['path'])
        catalog = gate._json(self.root / closure['regressionCatalog']['path'])
        results = [{'id': surface['id'], 'decision': 'clean', 'reason': 'Compared fixture regression.'} for surface in catalog]
        actual = self.write(f'translation/de/pipeline/{session}-regression-results.json', results)
        regression = self.write(f'translation/de/pipeline/{session}-regressions.json', {'closureSha256': closure_ref['sha256'], 'sessionId': session,
            'results': [{**r, 'evidence': actual} for r in results]})
        evidence += [handoff, regression, actual, *closure_evidence]
        return self.create('reviewer', {'handoff': handoff, 'reads': [bundle], 'findings': [], 'regressions': regression}, evidence, 'stage-complete', session)

    def test_inspection_exact_counts_and_canonical_hash(self):
        info = self.inspect()
        self.assertEqual(info['errors'], [])
        self.assertEqual((info['authoredVisible'], info['totalVisible'], info['technicalRetentions']), (3, 3, 1))
        self.assertEqual(info['corpusSha256'], gate._sha(gate._bytes(info['corpus'])))
        self.assertNotIn('technical', {r['id'] for r in info['corpus']})

    def test_unknown_protected_and_path_locale_rejected(self):
        for locale in ('ru', 'en', '../de', 'DE', 'unknown'):
            with self.assertRaisesRegex(ValueError, 'Unknown, protected or excluded'):
                gate.inspect_locale(self.root, locale)

    def test_wrong_source_duplicate_flags_and_locale(self):
        for mutation, expected in [
            (lambda b: b.update(siteLocale='fr'), 'Batch locale'),
            (lambda b: b['entries'].append(b['entries'][0]), 'Duplicate authored'),
            (lambda b: b['entries'][0].update(source='other'), 'changed exact source'),
            (lambda b: b['entries'][0].update(immediateEdit=False), 'immediateEdit')]:
            original = copy.deepcopy(self.batch)
            mutation(self.batch); self.save_batch()
            self.assertTrue(any(expected in e for e in self.inspect()['errors']))
            self.batch = original; self.save_batch()

    def test_local_classification_never_reduces_denominator(self):
        self.batch['entries'][1]['sourceRoleDisposition'] = {'role': 'preserve-exactly', 'reason': 'A local classification finding.'}
        self.batch['entries'].pop(); self.save_batch()
        info = self.inspect()
        self.assertEqual(info['totalVisible'], 3)
        self.assertEqual(info['missingIds'], ['c'])
        self.assertEqual(len(info['localClassificationFindings']), 1)

    def test_checkpoint_and_report_bytes_do_not_change_progress(self):
        before = self.progress()
        self.write('translation/de/CHECKPOINT.json', {'claims': 'complete'})
        self.write('translation/de/report.json', {'rows': list(range(500))})
        self.assertEqual(before, self.progress())
        record = self.create('editor', {}, [])
        result = self.validate(record)
        self.assertFalse(result['meaningfulProgress'])
        self.assertIn('Report-only continue', result['blockers'][0])

    def test_actual_author_repair_counts_and_unchanged_claim_does_not(self):
        before = self.progress()
        self.batch['entries'][0]['target'] = 'repaired-target-a'; self.save_batch()
        record = self.create('author', {'authoredIds': ['a']}, [], previous=before)
        self.assertTrue(self.validate(record)['meaningfulProgress'])
        second = self.create('author', {'authoredIds': ['a']}, [])
        self.assertIn('no actual new/changed', self.validate(second)['blockers'][0])

    def test_author_empty_continue_never_gets_stage_token_credit(self):
        result = self.validate(self.create('author', {}, []))
        self.assertFalse(result['meaningfulProgress'])
        self.assertIn('Report-only continue', result['blockers'][0])

    def test_replay_retains_real_accepted_authorship_without_new_semantic_credit(self):
        before=self.progress();self.batch['entries'][0]['target']='authored-a';self.save_batch()
        record=self.create('author',{'authoredIds':['a']},[],previous=before)
        validated=self.validate(record);self.assertTrue(validated['meaningfulProgress'])
        task,path,_=record;run=self.root/'runtime/cli-localization/runs/replay-test'
        self.write('runtime/cli-localization/current.json',{'run':str(run)})
        self.write('runtime/cli-localization/runs/replay-test/config.json',{})
        state={'locales':{'de':{'attempts':[{'taskId':task['id'],'pipelineRevision':2,'role':'author',
            'status':'continue','usage':{'session':task['sessionId'],'tokens':{'total':1}},'validation':validated}]}}}
        self.write('runtime/cli-localization/runs/replay-test/state.json',state)
        state_reads=[];read_json=gate._json
        def bounded_read(path):
            if Path(path)==run/'state.json':state_reads.append(str(path))
            return read_json(path)
        with patch.object(gate,'_json',side_effect=bounded_read):
            self.assertEqual(self.progress()['recordErrors'],[])
        self.assertEqual(len(state_reads),1,'One replay must not parse the entire queue once per receipt')
        self.batch['entries'][0]['target']='later-correction-a';self.save_batch()
        progress=self.progress();self.assertEqual(progress['recordErrors'],[]);self.assertEqual(progress['semanticCurrent'],0)
        # An empty new invocation remains report-only despite the accepted old work.
        self.assertIn('Report-only continue',self.validate(self.create('author',{},[]))['blockers'][0])

    def test_historical_authorship_requires_original_validation_and_exact_pins(self):
        before=self.progress();self.batch['entries'][0]['target']='authored-a';self.save_batch()
        record=self.create('author',{'authoredIds':['a']},[],previous=before);validated=self.validate(record)
        task,_,_=record;run=self.root/'runtime/cli-localization/runs/replay-test'
        self.write('runtime/cli-localization/current.json',{'run':str(run)})
        self.write('runtime/cli-localization/runs/replay-test/config.json',{})
        original={'taskId':task['id'],'pipelineRevision':2,'role':'author','status':'continue',
            'usage':{'session':task['sessionId'],'tokens':{'total':1}},'validation':validated}
        for change in ('no-original-progress','changed-receipt-pin','missing-task-pin'):
            row=copy.deepcopy(original)
            if change=='no-original-progress':row['validation']['meaningfulProgress']=False
            elif change=='changed-receipt-pin':row['validation']['savedEvidence'][0]['sha256']='changed'
            else:row['validation']['savedEvidence']=[r for r in row['validation']['savedEvidence'] if not r['path'].endswith('/task.json')]
            self.write('runtime/cli-localization/runs/replay-test/state.json',{'locales':{'de':{'attempts':[row]}}})
            self.assertTrue(any('Report-only continue' in e for e in self.progress()['recordErrors']),change)

    def test_accepted_author_replay_does_not_pin_mutable_status_as_translation(self):
        before=self.progress();self.batch['entries'][0]['target']='authored-a';self.save_batch()
        checkpoint=self.write('translation/de/CHECKPOINT.md',{'status':'old'})
        unresolved=self.write('translation/de/UNRESOLVED.md',{'remaining':'old'})
        actual=self.write('translation/de/pipeline/authored-proof.json',{'ids':['a']})
        record=self.create('author',{'authoredIds':['a']},[checkpoint,unresolved,actual],previous=before);validated=self.validate(record)
        self.assertTrue(validated['meaningfulProgress']);task,_,_=record;run=self.root/'runtime/cli-localization/runs/operational-replay'
        self.write('runtime/cli-localization/current.json',{'run':str(run)});self.write('runtime/cli-localization/runs/operational-replay/config.json',{})
        self.write('runtime/cli-localization/runs/operational-replay/state.json',{'locales':{'de':{'attempts':[{'taskId':task['id'],'pipelineRevision':2,'role':'author','status':'continue','usage':{'session':task['sessionId'],'tokens':{'total':1}},'validation':validated}]}}})
        self.write(checkpoint['path'],{'status':'new'});self.write(unresolved['path'],{'remaining':'new'});self.assertEqual(self.progress()['recordErrors'],[])
        self.write(actual['path'],{'ids':['changed']})
        self.assertTrue(any('Evidence SHA256 mismatch' in e for e in self.progress()['recordErrors']))

    def test_actual_partial_read_repeated_with_report_edit_is_not_progress(self):
        bundle, refs = self.bundle(['a'])
        first = self.create('editor', {'reads': [bundle]}, refs)
        self.assertTrue(self.validate(first)['meaningfulProgress'])
        second = self.create('editor', {'reads': [bundle]}, refs)
        result = self.validate(second)
        self.assertFalse(result['meaningfulProgress'])
        self.assertIn('Report-only continue', result['blockers'][0])

    def test_author_history_uses_exact_archived_bytes_without_reverting_current_text(self):
        before=self.progress();self.batch['entries'][0]['target']='authored-a';self.save_batch()
        original=self.ref('translation/de/batches/one.json')
        raw=(self.root/original['path']).read_bytes()
        record=self.create('author',{'authoredIds':['a']},[original],previous=before)
        validated=self.validate(record);self.assertTrue(validated['meaningfulProgress'])
        task,_,_=record
        archive=f'translation/de/pipeline/tasks/{task["id"]}/evidence-snapshots/original.json'
        p=self.root/archive;p.parent.mkdir(parents=True);p.write_bytes(raw);snapshot=self.ref(archive)
        run=self.root/'runtime/cli-localization/runs/archive-test'
        self.write('runtime/cli-localization/current.json',{'run':str(run)})
        self.write('runtime/cli-localization/runs/archive-test/config.json',{})
        row={'taskId':task['id'],'pipelineRevision':2,'role':'author','status':'continue',
             'usage':{'session':task['sessionId'],'tokens':{'total':1}},'validation':validated,
             'historicalEvidenceSnapshots':[{'original':original,'snapshot':snapshot}]}
        def save():self.write('runtime/cli-localization/runs/archive-test/state.json',{'locales':{'de':{'attempts':[row]}}})
        save();self.batch['entries'][0]['target']='later-corrected-a';self.save_batch()
        progress=self.progress();self.assertEqual(progress['recordErrors'],[])
        self.assertEqual(progress['semanticCurrent'],0)
        self.assertEqual(self.inspect()['corpus'][0]['target'],'later-corrected-a')
        # A current receipt cannot substitute historical bytes for current evidence.
        receipt_path=record[1];receipt_raw=receipt_path.read_bytes()
        current_doc=copy.deepcopy(record[2]);current_doc['outputBindings']=gate._bindings(self.inspect())
        self.write(str(receipt_path.relative_to(self.root)),current_doc)
        self.assertIn('Evidence SHA256 mismatch',self.validate(record)['blockers'][0])
        receipt_path.write_bytes(receipt_raw)
        p.write_text('tampered')
        self.assertTrue(any('Evidence SHA256 mismatch' in e for e in self.progress()['recordErrors']))
        p.write_bytes(raw);row['historicalEvidenceSnapshots'][0]['snapshot']['sha256']='wrong';save()
        self.assertTrue(any('preserve original bytes' in e for e in self.progress()['recordErrors']))
        row['historicalEvidenceSnapshots'][0]['snapshot']=snapshot
        row['validation']['meaningfulProgress']=False;save()
        self.assertTrue(any('Evidence SHA256 mismatch' in e for e in self.progress()['recordErrors']))

    def test_blocked_resources_keep_font_blocker_without_missing_verification_error(self):
        record=self.create('resources',{},[],'blocked');task,path,doc=record
        doc['blockers']=['Missing required script font coverage.']
        self.write(str(path.relative_to(self.root)),doc)
        with patch.object(gate,'_native_verification',side_effect=AssertionError('No completed build exists')):
            result=self.validate(record)
            self.assertFalse(result['roleComplete'])
            self.assertEqual(result['blockers'],doc['blockers'])
            self.assertEqual(self.progress()['recordErrors'],[])

    def test_blocked_receipt_preserves_actual_partial_work_without_handoff(self):
        bundle, refs = self.bundle(['a'])
        record = self.create('editor', {'reads': [bundle]}, refs, 'blocked')
        task, path, doc = record
        doc['blockers'] = ['Current-source glossary evidence is unavailable.']
        self.write(str(path.relative_to(self.root)), doc)
        result = self.validate(record)
        self.assertTrue(result['meaningfulProgress'])
        self.assertFalse(result['roleComplete'])
        self.assertEqual(result['progress']['semanticCurrent'], 1)

    def test_incomplete_author_and_editor_complete_claim_rejected(self):
        self.batch['entries'].pop(); self.save_batch()
        for role in ('author', 'editor'):
            record = self.create(role, {}, [], 'stage-complete')
            self.assertIn('Incomplete role-complete', self.validate(record)['blockers'][0])

    def test_partial_read_is_progress_and_cannot_claim_full(self):
        bundle, refs = self.bundle(['a'])
        record = self.create('editor', {'reads': [bundle]}, refs)
        result = self.validate(record)
        self.assertTrue(result['meaningfulProgress'], result['blockers'])
        self.assertFalse(result['roleComplete'])
        self.assertEqual(result['progress']['semanticCurrent'], 1)

    def test_generated_corpus_without_hashes_decisions_or_actual_ids_rejected(self):
        bundle, refs = self.bundle(['a', 'b', 'c'])
        self.write(bundle['rows']['path'], self.inspect()['corpus'])
        bundle['rows'] = self.ref(bundle['rows']['path'])
        refs = [bundle['rows'], bundle['ids'], bundle['decisions']]
        result = self.validate(self.create('editor', {'reads': [bundle]}, refs))
        self.assertIn('explicit per-ID', result['blockers'][0])

    def test_forged_full_coverage_ids_rejected(self):
        bundle, refs = self.bundle(['a'])
        refs.remove(bundle['ids']); bundle['ids'] = self.write(bundle['ids']['path'], ['a', 'b', 'c']); refs.append(bundle['ids'])
        result = self.validate(self.create('editor', {'reads': [bundle]}, refs))
        self.assertIn('Actual read IDs differ', result['blockers'][0])

    def test_hash_mismatch_and_cross_locale_and_symlink_rejected(self):
        good = self.write('translation/de/note.json', {'actual': 'evidence'})
        bad_refs = [{**good, 'sha256': '0' * 64}, self.write('translation/fr/note.json', {'other': 'locale'})]
        target = self.root / 'translation/de/link.json'; target.symlink_to(self.root / good['path'])
        bad_refs.append({'path': str(target.relative_to(self.root)), 'sha256': good['sha256']})
        for ref, reason in zip(bad_refs, ('SHA256 mismatch', 'Cross-locale', 'Symlink')):
            result = self.validate(self.create('editor', {}, [ref]))
            self.assertIn(reason, result['blockers'][0])

    def test_stale_inputs_and_unknown_role_rejected(self):
        record = self.create('editor', {}, [])
        task, path, doc = record
        doc['inputBindings']['inventorySha256'] = 'old'
        self.write(str(path.relative_to(self.root)), doc)
        self.write(str((path.parent / 'task.json').relative_to(self.root)), task)
        result = self.validate(record)
        self.assertIn('Stale input', result['blockers'][0])
        result = gate.validate_receipt(self.root, 'de', 'delivery', path, task, task['sessionId'])
        self.assertIn('Unknown/mismatched role', result['blockers'][0])

    def test_editor_handoff_is_not_acceptance(self):
        self.editor()
        result = gate.completion(self.root, 'de')
        self.assertFalse(result['ready'])
        self.assertTrue(result['gates']['fullSemanticCoverage'])
        self.assertFalse(result['gates']['independentClosureAndRegressions'])
        self.assertIn('imageTextInventoryAndPlans', result['remainingGates'])
        self.assertEqual((result['runtime'], result['visual']), ('not-run', 'not-run'))

    def test_clean_independent_read_and_distinct_session(self):
        editor, closure, refs = self.editor()
        self_review = self.reviewer(editor, closure, refs, session='editor')
        self.assertIn('self review', self.validate(self_review)['blockers'][0])
        # Invalid record stays immutable; its evidence cannot grant credit.
        review = self.reviewer(editor, closure, refs, session='fresh-reviewer')
        result = self.validate(review)
        self.assertTrue(result['roleComplete'], result['blockers'])
        final = gate.completion(self.root, 'de')
        self.assertTrue(final['gates']['independentClosureAndRegressions'], final['blockers'])
        self.assertFalse(final['ready'])

    def test_changed_unread_closure_row_rejected(self):
        editor, closure, refs = self.editor(closure_ids=('a', 'b'))
        result = self.validate(self.reviewer(editor, closure, refs, ids=('a',)))
        self.assertIn('exact closure/delta', result['blockers'][0])

    def test_unreproducible_closure_and_missing_regression_rejected(self):
        bundle, refs = self.bundle(['a', 'b', 'c'])
        compatibility, more = self.glossary_work(); refs += more
        closure, more = self.closure(('a', 'b')); refs += more
        doc = gate._json(self.root / closure['path']); doc['components']['runtimeBindings'] = []
        refs.remove(closure); closure = self.write(closure['path'], doc); refs.append(closure)
        result = self.validate(self.create('editor', {'reads': [bundle], 'glossaryCompatibility': compatibility, 'closure': closure}, refs, 'stage-complete'))
        self.assertIn('differs from dependency components', result['blockers'][0])

    def test_dependency_recipe_must_generate_the_component_lists(self):
        bundle, refs = self.bundle(['a', 'b', 'c'])
        compatibility, more = self.glossary_work(); refs += more
        closure, more = self.closure(('a', 'b')); refs += more
        doc = gate._json(self.root / closure['path'])
        recipe_ref = doc['recipe']
        recipe = gate._json(self.root / recipe_ref['path']); recipe['dependencies'] = []
        refs.remove(recipe_ref); doc['recipe'] = self.write(recipe_ref['path'], recipe); refs.append(doc['recipe'])
        refs.remove(closure); closure = self.write(closure['path'], doc); refs.append(closure)
        result = self.validate(self.create('editor', {'reads': [bundle], 'glossaryCompatibility': compatibility, 'closure': closure}, refs, 'stage-complete'))
        self.assertIn('does not reproduce exact closure', result['blockers'][0])

    def test_mandatory_regressions_cannot_be_renamed_away(self):
        bundle, refs = self.bundle(['a', 'b', 'c'])
        compatibility, more = self.glossary_work(); refs += more
        closure, more = self.closure(); refs += more
        doc = gate._json(self.root / closure['path'])
        old = doc['regressionCatalog']
        catalog = gate._json(self.root / old['path']); catalog.pop(0)
        refs.remove(old); doc['regressionCatalog'] = self.write(old['path'], catalog); refs.append(doc['regressionCatalog'])
        refs.remove(closure); closure = self.write(closure['path'], doc); refs.append(closure)
        result = self.validate(self.create('editor', {'reads': [bundle], 'glossaryCompatibility': compatibility, 'closure': closure}, refs, 'stage-complete'))
        self.assertIn('Mandatory regression surfaces missing', result['blockers'][0])

    def test_dependency_retirement_requires_exact_ids_and_actual_justification(self):
        editor, first, refs = self.editor(closure_ids=('a', 'b'))
        self.assertTrue(self.validate(self.reviewer(editor, first, refs, ids=('a', 'b')))['roleComplete'])
        second, refs2 = self.closure(ids=('a',), previous=first)
        claimed = self.create('editor', {'closure': second}, refs2, 'stage-complete')
        self.assertIn('Retired dependency IDs', self.validate(claimed)['blockers'][0])
        doc = gate._json(self.root / second['path'])
        reason = {'id': 'b', 'reason': 'Fixture consumer no longer depends on unchanged b.'}
        evidence = self.write('translation/de/pipeline/retirement-reason.json', reason)
        doc['retiredIds'] = ['b']; doc['retirementReasons'] = [{**reason, 'evidence': evidence}]
        refs2.remove(second); second = self.write(second['path'], doc); refs2 += [second, evidence]
        # New task uses the newly justified immutable closure revision.
        good = self.create('editor', {'closure': second}, refs2, 'stage-complete')
        self.assertTrue(self.validate(good)['roleComplete'])

    def test_unchanged_delta_does_not_require_old_nonregression_rows(self):
        editor, first, refs = self.editor(closure_ids=('a', 'b'))
        self.assertTrue(self.validate(self.reviewer(editor, first, refs, ids=('a', 'b')))['roleComplete'])
        editor2, second, refs2 = self.editor(ids=('c',), previous_closure=first, closure_ids=('a', 'b', 'c'))
        result = self.validate(self.reviewer(editor2, second, refs2, ids=('a', 'c'), session='delta-reader'))
        self.assertTrue(result['roleComplete'], result['blockers'])
        self.assertTrue(gate.completion(self.root, 'de')['gates']['independentClosureAndRegressions'])

    def test_copied_glossary_layers_and_stale_source_rejected(self):
        ref, refs = self.glossary_work()
        doc = gate._json(self.root / ref['path']); doc['layers'][1] = doc['layers'][0]
        refs.remove(ref); ref = self.write(ref['path'], doc); refs.append(ref)
        result = self.validate(self.create('editor', {'glossaryCompatibility': ref}, refs))
        self.assertIn('Two distinct', result['blockers'][0])
        ref, refs = self.glossary_work()
        self.write('master-source.json', [{'id': 'concept', 'term': 'CHANGED', 'meaning': 'Changed meaning.'}])
        result = self.validate(self.create('editor', {'glossaryCompatibility': ref}, refs))
        self.assertIn('Current canonical glossary source differs', result['blockers'][0])

    def test_resource_plaintext_or_zip_path_is_not_acceptance(self):
        fake = self.write('translation/de/zip-path.json', {'status': 'passed', 'archive': 'file.zip'})
        result = self.validate(self.create('package', {'verification': fake}, [fake], 'stage-complete'))
        self.assertFalse(result['roleComplete'])
        self.assertFalse(result['meaningfulProgress'])
        self.assertIn('buildManifest', result['blockers'][0])

    def test_native_helper_receipt_contract_positive_and_failure(self):
        editor, closure, refs = self.editor()
        self.assertTrue(self.validate(self.reviewer(editor, closure, refs))['roleComplete'])
        classification = {'asset': 'one.png', 'sourceSha256': 'image-source', 'classification': 'no-text', 'reason': 'Fixture contains no lettering.'}
        source_read = self.write('translation/de/pipeline/image-source-read.json', classification)
        image_inventory = self.write('translation/de/pipeline/image-inventory.json', [{**classification, 'evidence': source_read}])
        plans = self.write('translation/de/pipeline/image-plans.json', [])
        media = self.ref(gate.MEDIA_MANIFEST)
        image_doc = self.write('translation/de/pipeline/image-acceptance.json', {'sourceManifest': media, 'inventory': image_inventory, 'plans': plans})
        self.assertTrue(self.validate(self.create('editor', {'imageText': image_doc}, [image_doc, media, image_inventory, plans, source_read]))['meaningfulProgress'])
        manifest = self.write('build/multilingual-delivery/revision/manifest.json', {'siteLocale': 'de', 'files': [{'path': 'fixture', 'sha256': 'payload'}]})
        accepted = self.write('build/multilingual-delivery/revision/ACCEPTANCE.json', {'siteLocale': 'de', 'status': 'passed-technical-candidate', 'manifestSha256': manifest['sha256']})
        self.write('tools/multilingual/delivery/native_delivery.py', {'fixture': 'adapter process replaced in this unit test'})
        actual = {'status': 'passed-native-decrypted-readback', 'siteLocale': 'de', 'authoredEntries': 3, 'files': 1, 'mappedTargets': 0, 'archive': None}
        result = type('Result', (), {'returncode': 0, 'stdout': json.dumps(actual), 'stderr': ''})()
        with patch.object(gate.subprocess, 'run', return_value=result) as run:
            record = self.create('resources', {'verification': accepted, 'buildManifest': manifest}, [accepted, manifest], 'stage-complete')
            validated = self.validate(record)
            self.assertTrue(validated['roleComplete'], validated['blockers'])
            self.assertIn('verify', run.call_args.args[0])
            self.assertNotIn('build', run.call_args.args[0])
            archive = self.write('build/multilingual-delivery/revision.zip', {'fixture': 'native bytes checked by replaced adapter'})
            package_doc = dict(actual, archive=str(self.root / archive['path']), archiveSha256=archive['sha256'], buildManifestSha256=manifest['sha256'])
            package = self.write('build/multilingual-delivery/revision.zip.receipt.json', package_doc)
            result.stdout = json.dumps({k: v for k, v in package_doc.items() if k not in ['archiveSha256', 'buildManifestSha256']})
            record2 = self.create('package', {'verification': package, 'buildManifest': manifest, 'archive': archive}, [package, manifest, archive], 'stage-complete')
            self.assertTrue(self.validate(record2)['roleComplete'])
            completed = gate.completion(self.root, 'de')
            self.assertTrue(completed['ready'], completed)
            self.assertEqual(completed['runtime'], 'not-run')
            self.assertEqual(completed['visual'], 'not-run')
            result.returncode = 2; result.stderr = 'Decrypted native bytes differ'
            failed = self.validate(record2)
            self.assertFalse(failed['roleComplete'])
            self.assertIn('Decrypted native bytes differ', failed['blockers'][0])

    def test_legacy_partial_reads_import_real_ids_and_remain_preparatory(self):
        rows = [self.inspect()['corpus'][0]]
        rows_ref = self.write('translation/de/history/read.rows.json', rows)
        receipt_ref = self.write('translation/de/history/read.receipt.json', {
            'siteLocale': 'de', 'status': 'provisional-source-target-issue-collection',
            'actualReadCount': 1, 'actualReadIds': ['a'], 'rowsSha256': rows_ref['sha256']})
        item = {'format': 'fr-preparatory', 'receipt': receipt_ref, 'rows': rows_ref, 'sessionId': 'historical-reader'}
        record = self.create('editor', {'legacyReads': [item]}, [receipt_ref, rows_ref])
        result = self.validate(record)
        self.assertTrue(result['meaningfulProgress'], result['blockers'])
        self.assertEqual(result['progress']['preparatoryCurrent'], 1)
        self.assertEqual(result['progress']['semanticCurrent'], 0)
        # Operational schema/summary changes never require rereading valid pairs.
        repeated = self.create('editor', {'legacyReads': [item]}, [receipt_ref, rows_ref])
        self.assertFalse(self.validate(repeated)['meaningfulProgress'])

    def test_legacy_saved_page_filename_preserves_explicit_index_alias(self):
        base = 'translation/de/history'
        row = {**self.inspect()['corpus'][0], 'index': 0, 'batch': 'de-0001-fixture.json'}
        name = 'attempt-0001-rows-0001-0000-0001.jsonl'
        path = self.root / base / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row) + '\n'); rows = self.ref(str(path.relative_to(self.root)))
        ids_path = self.root / base / 'attempt-0001-read-ids.txt'; ids_path.write_text('a\n'); ids = self.ref(str(ids_path.relative_to(self.root)))
        catalog = {'path': str(self.root / 'translation/de/batches/de-0001-fixture.json'), 'sha256': 'fixture-original-batch', 'count': 1, 'pages': [[0, 1]], 'decision': 'Actual saved complete pair read.'}
        decisions = self.write(base + '/attempt-0001-decisions.json', {'catalogs': [catalog]})
        receipt = self.write(base + '/attempt-0001-receipt.json', {
            'siteLocale': 'de', 'sourceInventorySha256': gate.INVENTORY_SHA256, 'glossarySnapshotSha256': self.inspect()['glossarySha256'],
            'catalogs': [catalog], 'evidence': {Path(r['path']).name: r['sha256'] for r in [rows, ids, decisions]}})
        ev = gate.Evidence(self.root, 'de', [receipt])
        pairs = gate._legacy_read(ev, {'format': 'es-catalogs', 'receipt': receipt, 'sessionId': 'historical-reader'}, self.inspect())
        self.assertEqual(set(pairs), {'a'})
        self.assertEqual(pairs['a']['pairSha256'], gate._pair(self.inspect()['corpus'][0]))

    def test_historical_findings_cannot_disappear_when_full_read_is_imported(self):
        corpus = self.inspect()['corpus']
        rows = self.write('translation/de/history/paired-read-rows.json', corpus)
        ids = self.write('translation/de/history/paired-read-ids.json', ['a', 'b', 'c'])
        ids_path = self.root / 'translation/de/history/paired-read-ids.txt'
        ids_path.write_text('a\nb\nc\n'); ids = self.ref(str(ids_path.relative_to(self.root)))
        finding = {'id': 'b', 'source': 'source-b', 'reviewedTarget': 'target-b', 'proposedTarget': 'repair-b', 'reason': 'Concrete fixture omission.'}
        findings = self.write('translation/de/history/findings.json', [finding])
        receipt = self.write('translation/de/history/legacy-part.json', {
            'siteLocale': 'de', 'inventorySha256': gate.INVENTORY_SHA256, 'glossarySnapshotSha256': self.inspect()['glossarySha256'],
            'readingMethod': 'Actual complete paired read retained in the listed artifacts.',
            'evidenceHashes': {str(Path(r['path']).relative_to('translation/de')): r['sha256'] for r in [rows, ids, findings]}})
        record = self.create('editor', {'legacyReads': [{'format': 'de-parts', 'receipt': receipt, 'sessionId': 'original-reader'}]}, [receipt])
        result = self.validate(record)
        self.assertEqual(result['progress']['semanticCovered'], 3)
        self.assertEqual(len(result['progress']['openLegacyFindingKeys']), 1)
        compatibility, refs = self.glossary_work()
        closure, more = self.closure(); refs += more
        claimed = self.create('editor', {'glossaryCompatibility': compatibility, 'closure': closure}, refs, 'stage-complete')
        self.assertIn('historical finding dispositions: 1 remaining', self.validate(claimed)['blockers'][0])

    def test_actual_reads_survive_an_invalid_operational_completion_claim(self):
        bundle, refs = self.bundle(['a', 'b', 'c'])
        old = self.create('editor', {'reads': [bundle]}, refs, 'stage-complete')
        self.assertFalse(self.validate(old)['roleComplete'])
        ref = self.ref(str(old[1].relative_to(self.root)))
        repaired_schema = self.create('editor', {'importReads': [{'receipt': ref, 'bundleIndices': [0]}]}, [ref], session='new-editor')
        result = self.validate(repaired_schema)
        self.assertTrue(result['meaningfulProgress'], result['blockers'])
        self.assertEqual(result['progress']['semanticCovered'], 3)
        self.assertFalse(result['roleComplete'])

    def test_latest_handoff_cannot_inherit_acceptance_for_unread_new_closure(self):
        editor, first, refs = self.editor()
        self.assertTrue(self.validate(self.reviewer(editor, first, refs))['roleComplete'])
        self.assertTrue(gate.completion(self.root, 'de')['gates']['independentClosureAndRegressions'])
        second, more = self.closure(ids=('a', 'b'), previous=first)
        handoff = self.create('editor', {'closure': second}, more, 'stage-complete')
        self.assertTrue(self.validate(handoff)['roleComplete'])
        self.assertFalse(gate.completion(self.root, 'de')['gates']['independentClosureAndRegressions'])

    def test_current_control_failure_does_not_erase_verified_old_semantic_pairs(self):
        self.editor()
        with patch.object(gate, '_validate_controls', side_effect=gate.GateError('Concrete current control defect')):
            snapshot = self.progress()
            self.assertEqual(snapshot['semanticCovered'], 3)
            self.assertTrue(snapshot['structuralErrors'])
            before = snapshot
            self.batch['entries'][0]['target'] = 'new-invalid-target'; self.save_batch()
            result = self.validate(self.create('author', {'authoredIds': ['a']}, [], previous=before))
            self.assertFalse(result['meaningfulProgress'])
            self.assertIn('fail structural validation', result['blockers'][0])

    def test_explicit_images_cannot_waive_media_inventory(self):
        inventory = self.write('translation/de/pipeline/images.json', [])
        plans = self.write('translation/de/pipeline/plans.json', [])
        media = self.ref(gate.MEDIA_MANIFEST)
        doc = self.write('translation/de/pipeline/image-evidence.json', {'sourceManifest': media, 'inventory': inventory, 'plans': plans})
        result = self.validate(self.create('editor', {'imageText': doc}, [doc, media, inventory, plans]))
        self.assertIn('omits/duplicates', result['blockers'][0])

    def test_replayed_evidence_mutation_invalidates_credit(self):
        editor, closure, refs = self.editor()
        self.assertEqual(self.progress()['semanticCurrent'], 3)
        self.write(refs[0]['path'], [])
        after = self.progress()
        self.assertEqual(after['semanticCurrent'], 0)
        self.assertTrue(any('SHA256 mismatch' in e for e in after['recordErrors']))

    def test_delta_retains_unaffected_baseline_and_requires_new_ids(self):
        editor, first_closure, refs = self.editor(closure_ids=('a', 'b'))
        first = self.reviewer(editor, first_closure, refs, ids=('a', 'b'))
        self.assertTrue(self.validate(first)['roleComplete'])
        # Only b changes. a is mandatory regression; c enters closure for the first time.
        self.batch['entries'][1]['target'] = 'corrected-b'; self.save_batch()
        editor2, closure2, refs2 = self.editor(ids=('b',), previous_closure=first_closure, changed=('b',), closure_ids=('a', 'b', 'c'))
        bad = self.reviewer(editor2, closure2, refs2, ids=('a', 'b'), session='delta-missing-c')
        self.assertIn('exact closure/delta', self.validate(bad)['blockers'][0])
        good = self.reviewer(editor2, closure2, refs2, ids=('a', 'b', 'c'), session='delta-reader')
        result = self.validate(good)
        self.assertTrue(result['roleComplete'], result['blockers'])
        self.assertEqual(result['progress']['semanticCovered'], 3)
        self.assertTrue(gate.completion(self.root, 'de')['gates']['independentClosureAndRegressions'])


if __name__ == '__main__':
    unittest.main()
