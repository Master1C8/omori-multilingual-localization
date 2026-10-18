"""Read-only authoring input regressions, including real pinned corpus/glossary."""
import json
import unittest

import ru_workset as w


class WorksetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = w.glossary(w.ROOT)
        cls.units = w.corpus(w.ROOT)

    def test_meaning_only_item_remains_discoverable_with_complete_fields(self):
        hits = w.search(self.glossary, ['POOL NOODLE'])
        self.assertIn('mailbox', [r['id'] for r in hits])
        row = w.select_entries(self.glossary, ['mailbox'], 10000)[0]
        self.assertIn('ПАЛКИ ДЛЯ ПЛАВАНИЯ', row['RUmeaning'])
        self.assertEqual(row, next(x for x in self.glossary if x['id'] == 'mailbox'))

    def test_oversized_read_fails_before_partial_content_and_exact_limit_passes(self):
        row = next(x for x in self.glossary if x['id'] == 'mailbox')
        required = len(json.dumps([row], ensure_ascii=False))
        with self.assertRaisesRegex(ValueError, 'Complete glossary fields exceed'):
            w.select_entries(self.glossary, ['mailbox'], required - 1)
        self.assertEqual(w.select_entries(self.glossary, ['mailbox'], required), [row])
        with self.assertRaisesRegex(ValueError, 'Unknown glossary IDs'):
            w.select_entries(self.glossary, ['not-a-canonical-id'], required)

    def test_paginated_actual_source_has_no_missing_or_repeated_rows(self):
        asset = 'languages/en/Bestiary.HERO'
        expected = [u for u in self.units if u['asset'] == asset]
        rows, offset = [], 0
        while offset is not None:
            page = w.source_page(self.units, {}, asset, offset, 2500)
            rows.extend(page['rows'])
            offset = page['nextOffset']
        self.assertEqual([r['ordinal'] for r in rows], list(range(len(expected))))
        self.assertEqual([r['source'] for r in rows], [u['source'] for u in expected])
        with self.assertRaisesRegex(ValueError, 'One complete source unit exceeds'):
            w.source_page(self.units, {}, asset, 0, 1)
        with self.assertRaisesRegex(ValueError, 'Unknown source asset'):
            w.source_page(self.units, {}, 'missing', 0, 2500)

    def test_existing_targets_are_context_not_new_authorship(self):
        targets = w.authored(w.ROOT, self.units)
        self.assertGreater(len(targets), 0)
        u = next(u for u in self.units if u['id'] in targets)
        page = w.source_page(self.units, targets, u['asset'], 0, 1000000)
        row = next(r for r in page['rows'] if r['path'] == u['path'])
        self.assertEqual(row['authoredTarget'], targets[u['id']])


if __name__ == '__main__':
    unittest.main()
