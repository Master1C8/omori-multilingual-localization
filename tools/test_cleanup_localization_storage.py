"""Boundaries of the owner-authorized storage cleanup; no game/translation QA."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cleanup_localization_storage as cleanup


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='omori-cleanup-test-')
        self.base = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def file(self, name, value=b'payload'):
        p = self.base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)
        return p

    def test_link_preserves_real_bytes_and_other_files(self):
        a = self.file('a');b = self.file('b');zipfile = self.file('ready.zip', b'keep ZIP')
        cleanup.link_identical(b, a, cleanup.signature(b), cleanup.signature(a), cleanup.digest(a))
        self.assertEqual(a.stat().st_ino, b.stat().st_ino)
        self.assertEqual(b.read_bytes(), b'payload')
        self.assertEqual(zipfile.read_bytes(), b'keep ZIP')

    def test_changed_bytes_rejected_after_identity_guards_pass(self):
        a = self.file('a');b = self.file('b', b'changed')
        with self.assertRaisesRegex(ValueError, 'File bytes changed before mutation'):
            cleanup.link_identical(b, a, cleanup.signature(b), cleanup.signature(a), cleanup.digest(a))
        self.assertEqual(b.read_bytes(), b'changed')
        self.assertNotEqual(a.stat().st_ino, b.stat().st_ino)

    def test_between_files_failure_retains_first_commit_and_second_original(self):
        a = self.file('a');b = self.file('b');c = self.file('c');original_c = c.stat().st_ino
        cleanup.link_identical(b, a, cleanup.signature(b), cleanup.signature(a), cleanup.digest(a))
        with patch.object(cleanup.os, 'replace', side_effect=OSError('injected publish failure')):
            with self.assertRaisesRegex(OSError, 'injected publish failure'):
                cleanup.link_identical(c, a, cleanup.signature(c), cleanup.signature(a), cleanup.digest(a))
        self.assertEqual(a.stat().st_ino, b.stat().st_ino)
        self.assertEqual(c.stat().st_ino, original_c)
        self.assertEqual(c.read_bytes(), b'payload')
        self.assertFalse(list(self.base.glob('.*cleanup-*')))

    def test_payload_inventory_excludes_active_locale_current_build_zip_and_translation(self):
        def build(locale, revision):
            base = 'runtime/multilingual/locales/' + locale + '/' + revision
            data = b'x' * 4096
            target = self.file(base + '/resources/catalog.yaml', data)
            archive = self.file(base + '/resources/ready.zip', data)
            rows = [{'path': 'resources/' + p.name, 'sha256': hashlib.sha256(data).hexdigest()}
                    for p in [target, archive]]
            self.file(base + '/receipt.json', json.dumps({'status': 'passed-plaintext', 'files': rows}).encode())
            return target
        allowed = build('es', 'old')
        current = build('es', 'current')
        active = build('hi', 'working')
        self.file('translation/es/batches/001.json', b'keep translation')
        with patch.object(cleanup, 'ROOT', self.base):
            selected = cleanup.payloads({'es'}, [current.parent.parent])
        self.assertEqual(set(selected), {str(allowed.relative_to(self.base))})
        self.assertNotIn(str(active.relative_to(self.base)), selected)

    def test_only_empty_or_exact_benign_warning_logs_are_disposable(self):
        p = self.file('stderr.log', b'')
        self.assertTrue(cleanup.benign_stderr(p))
        p.write_text('2026-10-17T00:00:00Z WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt[0]: prompt must be at most 128 characters path=file:///example/plugin.json\n')
        self.assertTrue(cleanup.benign_stderr(p))
        p.write_text('2026-10-17T00:00:00Z ERROR disk full\n')
        self.assertFalse(cleanup.benign_stderr(p))
        p.write_text('2026-10-17T00:00:00Z WARN codex_sandboxing::violation: denied\n')
        self.assertFalse(cleanup.benign_stderr(p))

    def test_real_evidence_logs_protected_but_cleanup_plan_is_not_an_evidence_pin(self):
        keep = 'runtime/cli-localization/run/jobs/es/attempt-1/stderr.log'
        discard = 'runtime/cli-localization/run/jobs/es/attempt-2/stderr.log'
        self.file('translation/es/pipeline/tasks/old/receipt.json', json.dumps({'path': keep}).encode())
        self.file('runtime/storage-cleanup/plan.json', json.dumps({'path': discard}).encode())
        with patch.object(cleanup, 'ROOT', self.base):
            self.assertEqual(cleanup.log_references(), {keep})


if __name__ == '__main__':
    unittest.main()
