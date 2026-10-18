"""Queue regressions: lane ownership, real progress, role handoff and final gates.

Model and game execution are replaced here. Native archive correctness is tested by
the delivery adapter; semantic content is reviewed by identifiable CLI reviewers.
"""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import localization_pipeline as pipeline


class PipelineTests(unittest.TestCase):
    def test_versioned_resource_candidate_is_pinned_and_tamper_fails_before_task_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';snapshot=run/'snapshot';snapshot.mkdir(parents=True)
            (snapshot/'acceptance-contract.json').write_text('{}')
            path=root/'runtime/multilingual/locales/ar/candidate-v4.json';path.parent.mkdir(parents=True);path.write_text('{}')
            ref={'path':str(path.relative_to(root)),'sha256':pipeline.queue.digest(path)}
            config={'pipelineSnapshotDirectory':'snapshot','pipelineSnapshotHashes':pipeline.queue.artifacts([snapshot])}
            row={'attempts':[],'status':'queued','workflow':{'role':'resources','resourceCandidate':ref}}
            state={'locales':{'ar':row}}
            info={'inventorySha256':'inventory','glossarySha256':'glossary','corpusSha256':'corpus','corpus':[],'missingIds':[]}
            task,_,_=pipeline.create_task(root,run,config,state,'ar',(info,{}))
            self.assertEqual(task['resourceCandidate'],ref)
            row['attempts']=[{'taskId':task['id']}];path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'candidate changed'):
                pipeline.create_task(root,run,config,state,'ar',(info,{}))
            self.assertFalse((root/'translation/ar/pipeline/tasks/ar-resources-0002').exists())

    def test_concrete_locale_hold_preserves_live_work_and_blocks_packaging_then_restores(self):
        hold={'reason':'New delivered renderer defect; preserve existing receipt until repaired.'}
        row={'status':'running','workflow':{'role':'resources'}}
        self.assertTrue(pipeline.apply_locale_hold(row,hold));self.assertEqual(row['status'],'running')
        row['status']='queued';row['workflow']['role']='package'
        self.assertTrue(pipeline.apply_locale_hold(row,hold));self.assertEqual(row['status'],'blocked')
        self.assertEqual(row['workflow']['role'],'package')
        self.assertFalse(pipeline.apply_locale_hold(row,None));self.assertEqual(row['status'],'queued')
        blocked={'status':'blocked','workflow':{'role':'resources','blockers':['Original actual failure']}}
        pipeline.apply_locale_hold(blocked,hold);pipeline.apply_locale_hold(blocked,None)
        self.assertEqual(blocked['workflow']['blockers'],['Original actual failure'])
        with self.assertRaisesRegex(ValueError,'concrete reason'):pipeline.apply_locale_hold(row,{})

    def test_large_machine_baselines_are_archived_without_mutating_saved_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=Path(tmp)/'result.json';result.write_text('{}')
            row={'workflow':{'role':'author'},'status':'running'}
            record={'role':'author','usage':{'session':'actual-session'},'resultPath':str(result)}
            evidence=[{'path':'exact-task.json','sha256':'task-hash'}]
            validated={'roleComplete':False,'meaningfulProgress':True,'savedEvidence':evidence,
                'progress':{'authoredVisible':100,'authoredPairHashes':['pair']*100,'workTokens':['token']*100}}
            pipeline.apply_transition(row,record,{'status':'continue','receipt':'receipt.json'},validated)
            archive=record['validationSnapshot'];self.assertEqual(pipeline.queue.digest(archive['path']),archive['sha256'])
            self.assertEqual(pipeline.queue.read(archive['path']),validated)
            self.assertNotIn('authoredPairHashes',row['workflow']['progress'])
            self.assertNotIn('workTokens',record['validation']['progress'])
            self.assertEqual(pipeline.compact_progress(row['workflow']['progress']),row['workflow']['progress'])
            self.assertEqual(record['validation']['savedEvidence'],evidence)
            self.assertEqual(len(validated['progress']['authoredPairHashes']),100)

    def test_timeout_envelope_reconciles_only_after_real_saved_progress_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();folder=root/'translation/pl/pipeline/tasks/pl-author-11';folder.mkdir(parents=True)
            receipt=folder/'receipt.json';result=folder/'result.json'
            pipeline.queue.write(receipt,{'disposition':'continue','sessionId':'real-session','blockers':[]})
            pipeline.queue.write(result,{'taskId':'pl-author-11','role':'author','status':'blocked','receipt':str(receipt)})
            task={'id':'pl-author-11','role':'author','receiptPath':str(receipt)}
            record={'resultPath':str(result),'usage':{'session':'real-session','tokens':{'total':1}}}
            fake=type('Acceptance',(),{'validate_receipt':staticmethod(lambda *args:{'roleComplete':False,'meaningfulProgress':True,'blockers':[]})})()
            with patch.object(pipeline,'acceptance',return_value=fake):
                with self.assertRaisesRegex(ValueError,'disposition differs'):pipeline.validate_response(root,'pl',record,task)
                pipeline.queue.write(folder/'gate-failure.json',{'status':'receipt-rejected-validation-timeout','taskId':task['id'],'sessionId':'real-session','evidence':[{'path':str(receipt.relative_to(root)),'sha256':pipeline.queue.digest(receipt)}]})
                original=result.read_bytes();response,_=pipeline.validate_response(root,'pl',record,task)
                self.assertEqual(response['status'],'continue');self.assertEqual(result.read_bytes(),original)
                self.assertEqual(record['responseNormalization']['originalResultSha256'],pipeline.queue.digest(result))
                fake.validate_receipt=lambda *args:{'roleComplete':False,'meaningfulProgress':False,'blockers':['Actual content guard failed']}
                with self.assertRaisesRegex(ValueError,'Actual content guard failed'):pipeline.validate_response(root,'pl',record,task)

    def test_interrupted_baseline_preparation_does_not_reserve_task_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);run = root / 'run'
            state = {'locales': {'de': {'status': 'queued', 'attempts': [], 'workflow': {'role': 'resources'}}}}
            fake = type('Acceptance', (), {'inspect_locale': staticmethod(lambda *args: {}),
                'progress_snapshot': staticmethod(lambda *args: (_ for _ in ()).throw(InterruptedError('observer handoff')))})()
            with patch.object(pipeline, 'acceptance', return_value=fake):
                with self.assertRaisesRegex(InterruptedError, 'observer handoff'):
                    pipeline.create_task(root, run, {}, state, 'de')
            self.assertFalse((root / 'translation/de/pipeline/tasks/de-resources-0001').exists())
            self.assertFalse((run / 'jobs/de/attempt-0001').exists())

    def test_owner_deferral_releases_packaged_lane_without_claiming_acceptance(self):
        state = {'reviewSchedule': {'phase': 'packaging', 'decision': {}}, 'locales': {
            'es': {'status': 'queued', 'workflow': {'role': 'delivery'}},
            'pl': {'status': 'queued', 'workflow': {'role': 'author'}}}}
        pipeline.fill_lanes(state, 1)
        verdict = {'ready': False, 'gates': {'visibleCorpus': True,
            'protectedNativeResources': True, 'nativeArchiveVerification': True,
            'fullSemanticCoverage': False, 'independentClosureAndRegressions': False},
            'remainingGates': ['fullSemanticCoverage', 'independentClosureAndRegressions']}
        fake = type('Acceptance', (), {'completion': staticmethod(lambda *args: verdict)})()
        with tempfile.TemporaryDirectory() as tmp, patch.object(pipeline, 'acceptance', return_value=fake):
            pipeline.finalize_locale(Path(tmp), Path(tmp), state, 'es')
            self.assertEqual(state['locales']['es']['status'], 'packaged-awaiting-review')
            self.assertFalse(state['locales']['es']['workflow']['delivery']['ready'])
            self.assertFalse(pipeline.advance_review_batch(state))
            pipeline.fill_lanes(state, 1)
            self.assertEqual(state['lanes'][0]['locale'], 'pl')
            # Changing only native archive verification must reject the candidate.
            verdict['gates']['nativeArchiveVerification'] = False
            pipeline.finalize_locale(Path(tmp), Path(tmp), state, 'es')
            self.assertEqual(state['locales']['es']['status'], 'blocked')

    def test_batch_review_starts_only_after_every_package_and_preserves_saved_evidence(self):
        state = {'reviewSchedule': {'phase': 'packaging', 'decision': {}}, 'locales': {
            'es': {'status': 'packaged-awaiting-review', 'workflow': {'role': 'delivery', 'lastReceipt': 'saved-es'}},
            'pl': {'status': 'running', 'workflow': {'role': 'package'}}}}
        self.assertFalse(pipeline.advance_review_batch(state))
        state['locales']['pl']['status'] = 'packaged-awaiting-review'
        self.assertTrue(pipeline.advance_review_batch(state))
        self.assertEqual(state['reviewSchedule']['phase'], 'reviewing')
        self.assertEqual(state['locales']['es']['workflow']['lastReceipt'], 'saved-es')
        self.assertTrue(all(row['workflow']['role'] == 'editor' for row in state['locales'].values()))
        self.assertFalse(pipeline.advance_review_batch(state))

    def test_review_schedule_owner_binding_is_required_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);run = root / 'run';run.mkdir()
            path = run / 'decision.json'
            pipeline.queue.write(path, {'authority': 'owner', 'instruction': 'Review after all packages',
                'deferFullEditorialReview': True, 'startReviewAfterAllPackages': True, 'locales': ['es']})
            config = {'reviewScheduleDecision': {'path': 'run/decision.json', 'sha256': pipeline.queue.digest(path)}}
            state = {'locales': {'es': {}}}
            pipeline.configure_review_schedule(root, run, config, state)
            self.assertTrue(pipeline.packaging_before_review(state))
            with self.assertRaisesRegex(ValueError, 'lost its owner binding'):
                pipeline.configure_review_schedule(root, run, {}, state)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'decision changed'):
                pipeline.configure_review_schedule(root, run, config, state)

    def test_future_editor_receives_own_saved_review_work_without_other_locale_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);run = root / 'run';snapshot = run / 'snapshot';snapshot.mkdir(parents=True)
            (snapshot / 'acceptance-contract.json').write_text('{}')
            config = {'pipelineSnapshotDirectory': 'snapshot', 'pipelineSnapshotHashes': pipeline.queue.artifacts([snapshot])}
            state = {'reviewSchedule': {'phase': 'reviewing', 'decision': {}}, 'locales': {
                'es': {'attempts': [], 'status': 'queued', 'workflow': {'role': 'editor', 'deferredWork': ['saved-es.json']}},
                'de': {'workflow': {'deferredWork': ['saved-de.json']}}}}
            info = {'inventorySha256': 'inventory', 'glossarySha256': 'glossary', 'corpusSha256': 'corpus', 'corpus': [], 'missingIds': []}
            task, folder, _ = pipeline.create_task(root, run, config, state, 'es', (info, {}))
            self.assertEqual(task['savedReviewWork'], ['saved-es.json'])
            self.assertNotIn('saved-de.json', (folder / 'brief.json').read_text())

    def test_blocked_language_keeps_its_lane_until_actual_delivery(self):
        state = {'locales': {l: {'status': 'queued', 'workflow': {'role': 'author'}}
                             for l in ['es', 'de', 'pl']}}
        pipeline.fill_lanes(state, 2)
        self.assertEqual([l['locale'] for l in state['lanes']], ['es', 'de'])
        state['locales']['es']['status'] = 'blocked'
        pipeline.fill_lanes(state, 2)
        self.assertEqual([l['locale'] for l in state['lanes']], ['es', 'de'])
        self.assertEqual(pipeline.next_candidate(state, set(), True), 'de')
        state['locales']['de']['status'] = 'local-scope-complete'
        pipeline.fill_lanes(state, 2)
        self.assertEqual([l['locale'] for l in state['lanes']], ['es', 'pl'])
        self.assertEqual(state['lanes'][1]['completed'], ['de'])

    def test_native_adapter_wait_does_not_start_a_different_locale_in_same_lane(self):
        state = {'lanes': [{'id': 1, 'locale': 'es'}], 'locales': {
            'es': {'status': 'queued', 'workflow': {'role': 'resources'}},
            'pl': {'status': 'queued', 'workflow': {'role': 'author'}}}}
        self.assertIsNone(pipeline.next_candidate(state, set(), False))
        self.assertEqual(state['locales']['es']['status'], 'waiting-native-adapter')
        self.assertEqual(pipeline.next_candidate(state, set(), True), 'es')

    def test_report_only_continue_is_rejected_and_saved_artifact_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'translation/es/pipeline/tasks/es-editor-1'
            folder.mkdir(parents=True)
            receipt = folder / 'receipt.json'
            receipt.write_text(json.dumps({'disposition': 'continue'}))
            response = folder / 'result.json'
            response.write_text(json.dumps({'taskId': 'es-editor-1', 'role': 'editor',
                'status': 'continue', 'receipt': str(receipt)}))
            task = {'id': 'es-editor-1', 'role': 'editor', 'receiptPath': str(receipt)}
            record = {'resultPath': str(response), 'usage': {'session': 'actual-cli-id', 'tokens': {'total': 10}}}
            fake = type('Acceptance', (), {'validate_receipt': staticmethod(lambda *args: {
                'roleComplete': False, 'meaningfulProgress': False})})()
            with patch.object(pipeline, 'acceptance', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'report-only'):
                    pipeline.validate_response(root, 'es', record, task)
            self.assertEqual(json.loads(receipt.read_text()), {'disposition': 'continue'})
            # Matching positive control changes only the measured result.
            fake.validate_receipt = lambda *args: {'roleComplete': False, 'meaningfulProgress': True}
            with patch.object(pipeline, 'acceptance', return_value=fake):
                _, verified = pipeline.validate_response(root, 'es', record, task)
            self.assertTrue(verified['meaningfulProgress'])

    def test_role_handoff_stays_in_same_locale_and_does_not_mark_complete(self):
        row = {'workflow': {'role': 'editor'}, 'status': 'running'}
        record = {'role': 'editor', 'usage': {'session': 'editor-session'}}
        pipeline.apply_transition(row, record, {'status': 'stage-complete', 'receipt': '/receipt'},
                                  {'roleComplete': True, 'meaningfulProgress': True, 'nextRole': 'reviewer'})
        self.assertEqual(row['status'], 'queued')
        self.assertEqual(row['workflow']['role'], 'reviewer')
        self.assertEqual(row['workflow']['stage'], 'editorial')

    def test_missing_final_archive_gate_cannot_be_replaced_by_ready_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = {'locales': {'es': {'status': 'queued', 'workflow': {'role': 'delivery'}}}}
            fake = type('Acceptance', (), {'completion': staticmethod(lambda *args: {
                'ready': False, 'blockers': ['Native archive readback absent']})})()
            with patch.object(pipeline, 'acceptance', return_value=fake):
                pipeline.finalize_locale(root, root, state, 'es')
            self.assertEqual(state['locales']['es']['status'], 'blocked')
            fake.completion = lambda *args: {'ready': True, 'archive': 'verified.zip'}
            with patch.object(pipeline, 'acceptance', return_value=fake):
                pipeline.finalize_locale(root, root, state, 'es')
            self.assertEqual(state['locales']['es']['status'], 'local-scope-complete')

    def test_cli_session_identity_is_bound_from_actual_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events, task_path = root / 'events.jsonl', root / 'task.json'
            events.write_text(json.dumps({'type': 'thread.started', 'thread_id': 'real-session-123'}) + '\n')
            job = {'task': {'id': 'es-reviewer-1'}, 'record': {
                'eventsPath': str(events), 'taskPath': str(task_path)}}
            pipeline.bind_session(job)
            self.assertEqual(json.loads(task_path.read_text())['sessionId'], 'real-session-123')
            self.assertEqual(job['record']['sessionId'], 'real-session-123')
            self.assertEqual(json.loads((root / 'brief.json').read_text())['sessionId'], 'real-session-123')

    def test_model_brief_preserves_full_machine_baseline_without_dumping_pair_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = {'id': 'es-editor-52', 'previousProgress': {'semanticCurrent': 20717,
                    'authoredPairHashes': ['pair-sha'] * 20717, 'workTokens': ['read-token'] * 20717}}
            pipeline.queue.write(root / 'task.json', task)
            original = (root / 'task.json').read_bytes()
            pipeline.write_task_brief(task, root)
            brief = pipeline.queue.read(root / 'brief.json')
            self.assertEqual(brief['previousProgress'], {'semanticCurrent': 20717})
            self.assertEqual(brief['machineBaselineCounts'], {'authoredPairHashes': 20717, 'workTokens': 20717})
            self.assertEqual((root / 'task.json').read_bytes(), original)
            self.assertLess((root / 'brief.json').stat().st_size, 1000)

    def test_surviving_task_group_is_not_treated_as_finished(self):
        record = {'pid': 10, 'processGroup': 10, 'resultPath': '/original/result.json'}
        child = {'ppid': 1, 'pgid': 10, 'started': 'child-birth', 'state': 'S', 'command': 'task-owned-child'}
        found = pipeline.observed_job_processes(record, {11: child})
        self.assertEqual(set(found), {'11'})
        self.assertEqual(pipeline.observed_job_processes(record, {11: dict(child, state='Z')}), {})

    def test_finished_bootstrap_result_is_validated_before_continuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'translation/es/pipeline/tasks/es-editor-1'
            folder.mkdir(parents=True)
            receipt, result, events, task_path = [folder / n for n in ['receipt.json', 'result.json', 'events.jsonl', 'task.json']]
            receipt.write_text(json.dumps({'disposition': 'continue'}))
            result.write_text(json.dumps({'taskId': 'es-editor-1', 'role': 'editor',
                                         'status': 'continue', 'receipt': str(receipt)}))
            events.write_text('\n'.join(json.dumps(e) for e in [
                {'type': 'thread.started', 'thread_id': 'actual-session'},
                {'type': 'item.started', 'item': {'type': 'command_execution', 'id': 'command1'}},
                {'type': 'item.completed', 'item': {'type': 'command_execution', 'id': 'command1'}},
                {'type': 'turn.completed', 'usage': {'input_tokens': 100, 'output_tokens': 20}}]))
            task_path.write_text(json.dumps({'id': 'es-editor-1', 'role': 'editor', 'receiptPath': str(receipt)}))
            record = {'role': 'editor', 'taskPath': str(task_path), 'resultPath': str(result), 'eventsPath': str(events)}
            state = {'locales': {'es': {'status': 'running', 'attempts': [record], 'workflow': {'role': 'editor'}}}}
            fake = type('Acceptance', (), {'validate_receipt': staticmethod(lambda *args: {
                'roleComplete': False, 'meaningfulProgress': True, 'nextRole': 'editor'})})()
            with patch.object(pipeline, 'acceptance', return_value=fake):
                pipeline.reconcile_finished_locale(root, root, state, 'es')
            self.assertEqual(state['locales']['es']['status'], 'queued')
            self.assertEqual(record['status'], 'continue')
            self.assertEqual(record['usage']['tokens']['total'], 120)
            self.assertIsNone(record['exitCode'])
            self.assertFalse(record['exitCodeObserved'])

    def test_detached_cli_stages_finish_one_lane_before_starting_next_language(self):
        self._run_detached_stage_fixture()

    def test_detached_cli_packages_all_languages_before_automatic_editorial_phase(self):
        self._run_detached_stage_fixture(defer=True)

    def _run_detached_stage_fixture(self, defer=False):
        # Real subprocesses/locks/result files; model and artifact acceptance are fixtures.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run, snapshot = root / 'run', root / 'run/pinned'
            snapshot.mkdir(parents=True)
            (snapshot / 'pipeline-worker.md').write_text('Fixture task {{TASK}}')
            (snapshot / 'pipeline-result.schema.json').write_text('{}')
            (snapshot / 'acceptance-contract.json').write_text('{}')
            pipeline.queue.write(run / 'snapshot/identity.json', {'root': str(root), 'master': str(root)})
            fake_cli = root / 'fixture_cli.py'
            fake_cli.write_text('''import json,sys
from pathlib import Path
task_path,result_path=map(Path,sys.argv[1:])
t=json.loads(task_path.read_text())
receipt=Path(t['receiptPath']);receipt.write_text(json.dumps({'disposition':'stage-complete'}))
result_path.write_text(json.dumps({'taskId':t['id'],'role':t['role'],'status':'stage-complete','receipt':str(receipt)}))
print(json.dumps({'type':'thread.started','thread_id':'fixture-'+t['id']}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))
''')
            config = {'jobs': 1, 'codex': '/fixture', 'toolingDirectory': 'tools',
                      'pipelineSnapshotDirectory': 'pinned', 'deliveryToolingDirectory': 'native',
                      'deliveryToolingHashes': pipeline.queue.artifacts([run / 'native']),
                      'pipelineSnapshotHashes': pipeline.queue.artifacts([snapshot]),
                      'queueLockFile': 'fixture.lock', 'master': str(root)}
            if defer:
                decision = run / 'decision.json'
                pipeline.queue.write(decision, {'authority': 'owner', 'instruction': 'Review after all packages',
                    'deferFullEditorialReview': True, 'startReviewAfterAllPackages': True, 'locales': ['es', 'pl']})
                config['reviewScheduleDecision'] = {'path': 'run/decision.json', 'sha256': pipeline.queue.digest(decision)}
            pipeline.queue.write(run / 'config.json', config)
            locales = {}
            for locale in ['es', 'pl']:
                pipeline.queue.write(root / 'translation' / locale / 'glossary-snapshot.json', {})
                locales[locale] = {'status': 'queued', 'attempts': [],
                                   'workflow': {'role': 'author', 'stage': 'translate-edit'}}
            state = {'locales': locales, 'lanes': [{'id': 1, 'locale': 'es'}]}
            pipeline.queue.write(run / 'state.json', state)
            fixture_info = {'inventorySha256': 'inventory', 'glossarySha256': 'glossary',
                            'corpusSha256': 'corpus', 'authoredVisible': 0, 'totalVisible': 0,
                            'corpus': [], 'missingIds': []}
            order = []
            class FixtureAcceptance:
                def inspect_locale(self, *args): return fixture_info
                def progress_snapshot(self, *args): return {}
                def validate_receipt(self, root, locale, role, *args):
                    order.append((locale, role))
                    return {'roleComplete': True, 'meaningfulProgress': True,
                            'nextRole': pipeline.NEXT_ROLE[role],
                            'progress': {'resourcesVerified': True, 'nativeArchiveVerified': True} if role == 'reviewer' else {}}
                def completion(self, root, locale):
                    order.append((locale, 'delivered'))
                    return {'ready': not defer, 'gates': {'visibleCorpus': True,
                        'protectedNativeResources': True, 'nativeArchiveVerification': True}} if not defer or pipeline.packaging_before_review(pipeline.queue.read(run / 'state.json')) else {'ready': True}
            def command(binary, cwd, output, schema, writable):
                tasks = list((cwd / 'pipeline/tasks').glob('*/task.json'))
                task = max(tasks, key=lambda p: int(p.parent.name.rsplit('-', 1)[1]))
                return [sys.executable, str(fake_cli), str(task), str(output)]
            sleep = time.sleep
            with patch.object(pipeline, 'acceptance', return_value=FixtureAcceptance()), \
                 patch.object(pipeline.queue, 'command', side_effect=command), \
                 patch.object(pipeline.time, 'sleep', side_effect=lambda _: sleep(0.01)):
                pipeline.execute(run)
            final = pipeline.queue.read(run / 'state.json')
            self.assertEqual(final['status'], 'complete')
            expected = ([(loc, role) for loc in ['es', 'pl'] for role in ['author', 'resources', 'package', 'delivered']]
                        + [(loc, role) for loc in ['es', 'pl'] for role in ['editor', 'reviewer', 'delivered']]) if defer else [
                            (loc, role) for loc in ['es', 'pl'] for role in ['author', 'editor', 'reviewer', 'resources', 'package', 'delivered']]
            self.assertEqual(order, expected)
            self.assertTrue(all(r['status'] == 'local-scope-complete' for r in final['locales'].values()))


if __name__ == '__main__':
    unittest.main()
