import unittest
from hashlib import sha256
from authoring_keys import target_key
from text_resource_adapter import verify_delivered_spans


class DeliveredSpanTests(unittest.TestCase):
    def setUp(self):
        self.original = '<key:850> old <logic:KEEP> old <end>'
        self.units = [
            {'id': 'first', 'source': 'old', 'span': [10, 13], 'role': 'visible'},
            {'id': 'second', 'source': 'old', 'span': [27, 30], 'role': 'visible'}]
        self.edits = [(self.units[0], {'target': 'длинная подпись'}),
                      (self.units[1], {'target': 'ещё'})]
        self.actual = '<key:850> длинная подпись <logic:KEEP> ещё <end>'

    def test_actual_boundaries_and_source_id_keys(self):
        result = verify_delivered_spans(self.original, self.actual, self.edits)
        self.assertEqual(result, {'first': 'длинная подпись', 'second': 'ещё'})
        self.assertEqual(target_key(self.units[0], 'source-id'), 'first')
        with self.assertRaisesRegex(ValueError, 'different exact authoring'):
            target_key(dict(self.units[0], path=[1, 'note']), 'display-path')

    def test_protected_gap_and_misplaced_target_reject(self):
        verify_delivered_spans(self.original, self.actual, self.edits)
        for bad in [self.actual.replace('KEEP', 'DROP'),
                    '<key:850> old <logic:KEEP> ещё <end> длинная подпись',
                    self.actual.replace('ещё', 'длинная подпись')]:
            with self.subTest(actual=bad), self.assertRaisesRegex(ValueError, 'exact source-span assembly'):
                verify_delivered_spans(self.original, bad, self.edits)

    def test_parent_digest_rejects_changed_original_outside_visible_spans(self):
        pinned = [(dict(unit, parentValueSha256=sha256(self.original.encode()).hexdigest()), entry)
                  for unit, entry in self.edits]
        verify_delivered_spans(self.original, self.actual, pinned)
        changed = self.original.replace('KEEP', 'DROP')
        with self.assertRaisesRegex(ValueError, 'Pinned original mixed field'):
            verify_delivered_spans(changed, self.actual.replace('KEEP', 'DROP'), pinned)


if __name__ == '__main__':
    unittest.main()
