#!/usr/bin/env python3
"""Exercise partial-write boundaries using reviewed inputs and disposable outputs.

The integration fixture replaces Git queries only; it exercises actual filesystem
writes. It cannot establish real Git, CLI, network or database behavior.
"""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import assemble_compact_public_glossary as assembly
import integrate_compact_public_glossary as integration


class WriteBoundaries(unittest.TestCase):
    def test_assembly_continues_after_second_file_failure(self):
        expected = assembly.read(assembly.BASE / 'assembly.json')['outputs']
        original_base = assembly.BASE
        original_replace = Path.replace
        with tempfile.TemporaryDirectory(prefix='.compact-assembly-test-', dir=assembly.ROOT / 'source') as folder:
            base = Path(folder)
            (base / 'parts').symlink_to(original_base / 'parts', target_is_directory=True)
            (base / 'review').symlink_to(original_base / 'review', target_is_directory=True)

            def fail_second(path, target):
                if Path(target) == base / 'approved-ru.json':
                    raise OSError('injected second output failure')
                return original_replace(path, target)

            with patch.object(assembly, 'BASE', base), contextlib.redirect_stdout(io.StringIO()):
                with patch.object(Path, 'replace', fail_second):
                    with self.assertRaisesRegex(OSError, 'injected second output failure'):
                        assembly.assemble()
                self.assertEqual(assembly.sha(base / 'approved-source.json'), expected['approved-source.json'])
                self.assertFalse((base / 'approved-ru.json').exists())
                self.assertFalse((base / 'assembly.json').exists())
                assembly.assemble()
                for name, digest in expected.items():
                    self.assertEqual(assembly.sha(base / name), digest)
                self.assertEqual(assembly.read(base / 'assembly.json')['outputs'], expected)

    def test_integration_exposes_partial_state_and_refuses_blind_retry(self):
        baseline = integration.read(integration.ROOT / 'source/compact-public-publication-baseline-2026-10-13.json')
        original_master = integration.MASTER
        original_replace = Path.replace
        with tempfile.TemporaryDirectory(prefix='.compact-integration-test-', dir=integration.ROOT / 'source') as folder:
            master = Path(folder)
            dest = master / 'data/games/omori'
            dest.mkdir(parents=True)
            (dest / 'glossary-review').mkdir()
            for name in ['glossary.json', 'glossary-translations.json', 'glossary-sources.md']:
                # The canonical site has already advanced to compact v2. This
                # historical integration scenario must restore its pinned
                # pre-integration blobs rather than copy today's live files.
                relative='data/games/omori/'+name
                raw=subprocess.check_output(['git','show',baseline['masterHead']+':'+relative],cwd=original_master)
                (dest / name).write_bytes(raw)
                self.assertEqual(integration.sha(dest / name),baseline['masterFileHashes'][relative])
            old_translation_bytes = (dest / 'glossary-translations.json').read_bytes()

            def git_fixture(*args):
                return {
                    ('git', 'status', '--porcelain'): '',
                    ('git', 'branch', '--show-current'): 'main',
                    ('git', 'rev-parse', 'HEAD'): baseline['masterHead'],
                    ('git', 'remote', 'get-url', 'origin'): baseline['masterRemote'],
                }[args]

            def fail_second(path, target):
                if Path(target) == dest / 'glossary-translations.json':
                    raise OSError('injected translation replacement failure')
                return original_replace(path, target)

            with patch.object(integration, 'MASTER', master), patch.object(integration, 'DEST', dest), patch.object(integration, 'run', git_fixture):
                with patch.object(Path, 'replace', fail_second):
                    with self.assertRaisesRegex(OSError, 'injected translation replacement failure'):
                        integration.main()
                self.assertEqual(integration.read(dest / 'glossary.json'), integration.read(integration.BASE / 'approved-source.json'))
                self.assertEqual((dest / 'glossary-translations.json').read_bytes(), old_translation_bytes)
                self.assertFalse((dest / 'glossary-review/en-ru-compact-2026-10-13/integration-receipt.json').exists())
                with self.assertRaisesRegex(AssertionError, 'Canonical input changed: data/games/omori/glossary.json'):
                    integration.main()
                self.assertEqual((dest / 'glossary-translations.json').read_bytes(), old_translation_bytes)


if __name__ == '__main__':
    unittest.main()
