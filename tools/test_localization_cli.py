"""Tests queue boundaries using fake CLI events; no model, native game or translation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('queue_cli', Path(__file__).with_name('localization_cli.py'))
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class QueueTests(unittest.TestCase):
    def test_exact_terminal_capacity_is_retryable_without_switching_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=Path(tmp)/'events.jsonl'
            capacity={'type':'turn.failed','error':{'message':'Selected model is at capacity. Please try a different model.'}}
            events.write_text(json.dumps(capacity)+'\n')
            self.assertEqual(cli.terminal_provider_failure(events),'terminal-model-capacity')
            row={};record={'eventsPath':str(events),'finished':cli.stamp()}
            for _ in range(2):
                cli.schedule_rate_limit(row,record)
                self.assertEqual(row['status'],'waiting-rate-limit')
                self.assertGreater(row['retryNotBefore'],cli.time.time())
            cli.schedule_rate_limit(row,record)
            self.assertEqual(row['status'],'needs-attention')
            self.assertIn('three cooldown attempts',row['error'])
            events.write_text(json.dumps(capacity)+'\n'+json.dumps({'type':'turn.completed','usage':{}})+'\n')
            self.assertFalse(cli.rate_limit_failure(events))
            events.write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':capacity['error']['message']}})+'\n'+json.dumps({'type':'turn.failed','error':{'message':'Unknown CLI failure'}})+'\n')
            self.assertFalse(cli.rate_limit_failure(events))
            events.write_text('{truncated\n'+json.dumps(capacity)+'\n')
            self.assertTrue(cli.rate_limit_failure(events))

    def test_telemetry_note_normalization_preserves_raw_result_and_validates_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); evidence = root / 'translation/es-419/check.json'
            cli.write(evidence, {'controls': 'fixture'})
            result = root / 'result.json'
            original = {'status': 'continue', 'stage': 'translate-edit', 'summary': 'Saved wording',
                        'evidence': ['translation/es-419/check.json', 'Token usage telemetry unavailable.']}
            cli.write(result, original); raw = result.read_bytes(); record = {'resultPath': str(result)}
            clean = cli.worker_result(record, root, 'es-419')
            self.assertEqual(clean, dict(original, evidence=['translation/es-419/check.json']))
            self.assertEqual(result.read_bytes(), raw)
            self.assertEqual(cli.read(record['metadataNormalization']['normalizedPath']), clean)
            bad = dict(original, evidence=['translation/es-419/missing.json', 'Token usage telemetry unavailable.'])
            cli.write(result, bad)
            with self.assertRaisesRegex(ValueError, 'Evidence missing'):
                cli.worker_result({'resultPath': str(result)}, root, 'es-419')
            cli.write(result, dict(original, evidence=['Token usage telemetry unavailable.']))
            with self.assertRaisesRegex(ValueError, 'missing real evidence'):
                cli.worker_result({'resultPath': str(result)}, root, 'es-419')

    def test_metadata_reconciliation_only_resumes_the_exact_finished_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); evidence = root / 'translation/es-419/check.json'
            cli.write(evidence, {'controls': 'fixture'})
            result = root / 'result.json'
            cli.write(result, {'status': 'continue', 'evidence': ['translation/es-419/check.json', 'Token usage telemetry unavailable.']})
            events = root / 'events.jsonl'
            events.write_text(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 100, 'output_tokens': 20}}))
            record = {'number': 13, 'pid': 999, 'exitCode': 0, 'resultPath': str(result), 'eventsPath': str(events)}
            state = {'locales': {'es-419': {'status': 'needs-attention', 'error': 'original rejection', 'attempts': [record]}}}
            config = {'metadataReconciliations': [{'locale': 'es-419', 'attempt': 13, 'resultSha256': cli.digest(result)}]}
            with patch.object(cli, 'ROOT', root), patch.object(cli, 'process_snapshot', return_value={999: {'command': str(result)}}):
                with self.assertRaisesRegex(ValueError, 'live writer'):
                    cli.reconcile_metadata(root, state, config)
            with patch.object(cli, 'ROOT', root), patch.object(cli, 'process_snapshot', return_value={}):
                cli.reconcile_metadata(root, state, config)
                cli.reconcile_metadata(root, state, config)
            self.assertEqual(state['locales']['es-419']['status'], 'queued')
            self.assertEqual(record['observerError'], 'original rejection')
            self.assertEqual(len(state['appliedMetadataRepairs']), 1)

    def test_adoption_waits_for_surviving_child_and_checks_process_birth(self):
        parent = {'ppid': 1, 'started': 'parent-birth', 'command': 'codex original'}
        child = {'ppid': 10, 'started': 'child-birth', 'command': 'python original'}
        proc = cli.AdoptedProcess({'10': parent, '11': child})
        orphan = dict(child, ppid=1, command='python after exec')
        with patch.object(cli, 'process_snapshot', return_value={11: orphan}):
            self.assertIsNone(proc.poll())
        with patch.object(cli, 'process_snapshot', return_value={11: dict(orphan, started='reused-pid-birth')}):
            self.assertEqual(proc.poll(), 'identified-task-tree-exited')
        self.assertIsNone(proc.returncode)

    def test_adopted_result_needs_terminal_success_and_keeps_exit_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); evidence = root / 'translation/es/batch.json'
            cli.write(evidence, {'entries': ['saved actual fixture']})
            result = root / 'result.json'; cli.write(result, {'status': 'continue', 'evidence': ['translation/es/batch.json']})
            events = root / 'events.jsonl'; events.write_text('')
            def invoke():
                state = {'locales': {'es': {'status': 'running'}}}
                record = {'eventsPath': str(events), 'resultPath': str(result)}
                with patch.object(cli, 'ROOT', root):
                    cli.finish_adopted(root, state, 'es', record)
                return state['locales']['es'], record
            row, record = invoke()
            self.assertEqual(row['status'], 'needs-attention')
            self.assertIn('successful terminal turn', row['error'])
            events.write_text(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 100, 'output_tokens': 20}}))
            row, record = invoke()
            self.assertEqual(row['status'], 'queued')
            self.assertIsNone(record['exitCode'])
            self.assertFalse(record['exitCodeObserved'])

    def test_capacity_six_adopts_three_and_dispatches_exactly_three_others(self):
        class EndFirstIteration(Exception):
            pass
        class Live:
            def poll(self):
                return None
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = root / 'run'; snapshot = run / 'snapshot'
            cli.write(snapshot / 'identity.json', {'root': str(root), 'master': str(root)})
            config = {'jobs': 6, 'snapshotHashes': cli.artifacts([snapshot]), 'adoptionManifest': 'adoption.json',
                      'queueLockFile': 'queue-v5.lock', 'rendererRisk': 'accepted-static'}
            cli.write(run / 'config.json', config)
            locales = {}
            adoption = {}
            for n, loc in enumerate(['es', 'es-419', 'pt-BR']):
                record = {'pid': n + 100, 'resultPath': str(run / loc / 'result.json')}
                locales[loc] = {'status': 'running', 'attempts': [record]}
                adoption[loc] = dict(record, processes={})
            for loc in ['de', 'fr', 'tr', 'zh-TW']:
                locales[loc] = {'status': 'queued', 'attempts': []}
            cli.write(run / 'adoption.json', {'locales': adoption})
            cli.write(run / 'state.json', {'bootstrap': {'status': 'superseded-by-owner', 'toolingHashes': {}}, 'locales': locales})
            dispatched = []
            def launch(run, config, state, locale, fd):
                dispatched.append(locale)
                state['locales'][locale]['status'] = 'running'
                return (Live(), None, None, None, {})
            with patch.multiple(cli, ROOT=root, MASTER=root, CONTROL=root / 'runtime/cli-localization'), \
                 patch.object(cli, 'AdoptedProcess', return_value=Live()), \
                 patch.object(cli, 'glossary_available', return_value=True), \
                 patch.object(cli, 'launch_attempt', side_effect=launch), \
                 patch.object(cli.time, 'sleep', side_effect=EndFirstIteration):
                with self.assertRaises(EndFirstIteration):
                    cli.execute(run)
            self.assertEqual(dispatched, ['de', 'fr', 'tr'])

    def test_explicit_model_and_narrow_writable_roots(self):
        args = cli.command('/codex', Path('/project/translation/es'), Path('/result'), Path('/schema'), [Path('/project/build/es')])
        self.assertIn('gpt-6.1-sol', args)
        self.assertIn('model_reasoning_effort="high"', args)
        self.assertIn('model_provider="omori_https"', args)
        self.assertIn('model_providers.omori_https={name="OpenAI HTTPS",wire_api="responses",requires_openai_auth=true,supports_websockets=false}', args)
        self.assertNotIn('model_providers.openai.supports_websockets=false', args)
        self.assertIn('--approve-for-me', args)
        self.assertNotIn('resume', args)
        self.assertNotIn('--worktree', args)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', args)
        self.assertEqual(args[args.index('-C') + 1], '/project/translation/es')
        self.assertEqual(args[args.index('--add-dir') + 1], '/project/build/es')

    def test_lock_survives_observer_close_until_worker_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lock'
            fd = cli.acquire(path)
            child = subprocess.Popen(['python3', '-c', 'import sys; sys.stdin.read()'],
                                     stdin=subprocess.PIPE, pass_fds=(fd,))
            try:
                cli.os.close(fd)
                with self.assertRaisesRegex(RuntimeError, 'still live'):
                    cli.acquire(path)
                child.communicate(b'')
                new = cli.acquire(path)
                cli.os.close(new)
            finally:
                if child.poll() is None:
                    child.terminate(); child.wait()

    def test_usage_no_subset_double_count_and_unknown_reasoning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'events'
            events = [{'type': 'thread.started', 'thread_id': 'new-session'},
                      {'type': 'turn.completed', 'usage': {'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 20}},
                      {'type': 'turn.completed', 'usage': {'input_tokens': 50, 'cached_input_tokens': 30, 'output_tokens': 10, 'reasoning_output_tokens': 5}}]
            p.write_text('\n'.join(json.dumps(e) for e in events) + '\npartial')
            u = cli.usage(p)
            self.assertEqual(u['session'], 'new-session')
            self.assertEqual(u['tokens']['total'], 180)
            self.assertEqual(u['tokens']['cached_input'], 110)
            self.assertIsNone(u['tokens']['reasoning'])
            p.write_text(json.dumps(events[0]))
            self.assertIsNone(cli.usage(p)['tokens'])

    def test_locale_cannot_borrow_russian_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for loc in ['es', 'ru']:
                p = root / 'translation' / loc / 'evidence.json'
                p.parent.mkdir(parents=True); p.write_text('{}')
            r = {'status': 'local-scope-complete', 'evidence': ['translation/es/evidence.json']}
            cli.validate_result(r, root, 'es')
            with self.assertRaisesRegex(ValueError, 'another locale'):
                cli.validate_result(dict(r, evidence=['translation/ru/evidence.json']), root, 'es')

    def test_continue_accepts_same_locale_nonempty_batch_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for locale in ['es', 'ru']:
                p = root / 'translation' / locale / 'batches' / 'one.json'
                p.parent.mkdir(parents=True); p.write_text('{"entries":[]}')
            r = {'status': 'continue', 'evidence': [str(root / 'translation/es/batches')]}
            cli.validate_result(r, root, 'es')
            with self.assertRaisesRegex(ValueError, 'another locale'):
                cli.validate_result(dict(r, evidence=[str(root / 'translation/ru/batches')]), root, 'es')
            with self.assertRaisesRegex(ValueError, 'Evidence missing'):
                cli.validate_result(dict(r, status='local-scope-complete'), root, 'es')
            empty = root / 'translation/es/empty'; empty.mkdir()
            with self.assertRaisesRegex(ValueError, 'Evidence missing'):
                cli.validate_result(dict(r, evidence=[str(empty)]), root, 'es')

    def test_preparation_requires_actual_supplement_and_protected_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = [{'id': 'one', 'source': 'NO', 'asset': 'a', 'path': [1]}]
            extra = [{'id': 'native', 'source': 'YES', 'asset': 'a', 'path': [2]}]
            cli.write(root / 'source/text-corpus-8879120-02/units.json', base)
            cli.write(root / 'source/native-yaml-8879120-01/units.json', extra)
            inv = root / 'source/multilingual/units.json'
            cli.write(inv, base + extra)
            evidence = root / 'source/multilingual/test.json'; cli.write(evidence, {'checks': 'passed'})
            gate = root / 'source/multilingual/acceptance.json'
            receipt = {'source': 'passed', 'adapters': 'passed', 'inventoryPath': 'source/multilingual/units.json',
                       'inventorySha256': cli.digest(inv), 'evidence': [{'path': 'source/multilingual/test.json', 'sha256': cli.digest(evidence)}]}
            cli.write(gate, receipt); cli.validate_preparation(root)
            cli.write(inv, base)
            receipt['inventorySha256'] = cli.digest(inv); cli.write(gate, receipt)
            with self.assertRaisesRegex(ValueError, 'supplemental ID'):
                cli.validate_preparation(root)
            changed = base + [dict(extra[0], source='TRUE')]
            cli.write(inv, changed); receipt['inventorySha256'] = cli.digest(inv); cli.write(gate, receipt)
            with self.assertRaisesRegex(ValueError, 'Original source record changed'):
                cli.validate_preparation(root)

    def test_failed_request_does_not_retry_or_erase_prior_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'translation/es'; out.mkdir(parents=True)
            p = out / 'authored.json'; p.write_text('real earlier write')
            log = root / 'events'; log.write_text('')
            record = {'eventsPath': str(log), 'resultPath': str(root / 'missing-result')}
            state = {'locales': {'es': {'status': 'running'}}}
            fd = cli.acquire(root / 'lock')
            proc = type('Finished', (), {'returncode': 1})()
            with patch.object(cli, 'ROOT', root):
                cli.finish(root, state, 'es', (proc, fd, {}, [out], record))
            self.assertEqual(state['locales']['es']['status'], 'needs-attention')
            self.assertEqual(p.read_text(), 'real earlier write')
            self.assertIn('no automatic resubmission', state['locales']['es']['error'])

    def test_terminal_429_cools_down_without_losing_authored_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'translation/es'; out.mkdir(parents=True)
            p = out / 'authored.json'; p.write_text('preserved authored wording')
            log = root / 'events'
            failure = {'type': 'turn.failed', 'error': {'message': 'exceeded retry limit, last status: 429 Too Many Requests'}}
            log.write_text(json.dumps(failure))
            record = {'eventsPath': str(log), 'resultPath': str(root / 'missing-result')}
            state = {'locales': {'es': {'status': 'running'}}}
            fd = cli.acquire(root / 'lock')
            proc = type('Finished', (), {'returncode': 1})()
            with patch.object(cli, 'ROOT', root):
                cli.finish(root, state, 'es', (proc, fd, {}, [out], record))
            self.assertEqual(state['locales']['es']['status'], 'waiting-rate-limit')
            self.assertGreater(state['locales']['es']['retryNotBefore'], cli.time.time())
            self.assertEqual(p.read_text(), 'preserved authored wording')
            self.assertIsNone(record['usage']['tokens'])
            log.write_text(json.dumps(dict(failure, error={'message': '401 Unauthorized'})))
            self.assertFalse(cli.rate_limit_failure(log))
            log.write_text(json.dumps(failure) + '\n' + json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}))
            self.assertFalse(cli.rate_limit_failure(log))


if __name__ == '__main__':
    unittest.main()
