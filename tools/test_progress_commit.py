"""Failure between evidence and progress writes, using real temporary files."""
import tempfile
import unittest
from pathlib import Path
from source_prepare import strict_json
from reconcile_ru_progress import atomic_json, write_reconciliation


class ProgressCommit(unittest.TestCase):
    def test_interrupted_after_evidence_keeps_prior_index_then_reconciles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);index = root / 'index.json';first = root / 'evidence-1.json'
            atomic_json(index, {'count':1})
            def fail_between_writes():
                raise RuntimeError('injected interruption after evidence commit')
            with self.assertRaisesRegex(RuntimeError, 'after evidence commit'):
                write_reconciliation(first, index, {'verifiedCount':2}, {'count':2}, fail_between_writes)
            self.assertEqual(strict_json(first.read_bytes()), {'verifiedCount':2})
            self.assertEqual(strict_json(index.read_bytes()), {'count':1})
            write_reconciliation(root / 'evidence-2.json', index, {'verifiedCount':2}, {'count':2})
            self.assertEqual(strict_json(index.read_bytes()), {'count':2})
            with self.assertRaisesRegex(ValueError, 'Preserve earlier'):
                write_reconciliation(first, index, {'verifiedCount':3}, {'count':3})
            self.assertEqual(strict_json(index.read_bytes()), {'count':2})

    def test_second_output_encoding_failure_keeps_old_file_and_new_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);index = root / 'index.json';evidence = root / 'evidence.json'
            atomic_json(index, {'count':1})
            with self.assertRaisesRegex(ValueError, 'Out of range float'):
                write_reconciliation(evidence, index, {'verifiedCount':2}, {'count':float('nan')})
            self.assertEqual(strict_json(index.read_bytes()), {'count':1})
            self.assertEqual(strict_json(evidence.read_bytes()), {'verifiedCount':2})
            self.assertEqual(list(root.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
