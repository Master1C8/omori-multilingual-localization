"""Exact term preservation, gender attribution, overrides and stale-reference guards."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ru_workset as w
import build_ru_compact_glossary as c


class CompactGlossaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document, cls.rows = w.compact_glossary(w.ROOT)
        cls.by_id = {row['id']: row for row in cls.rows}

    def test_all_699_exact_order_and_terms(self):
        full = w.glossary(w.ROOT)
        self.assertEqual(len(full), 699)
        self.assertEqual([(r['id'], r['en'], r['ru']) for r in self.rows],
                         [(r['id'], r['ENterm'], r['RUterm']) for r in full])

    def test_pronoun_subject_and_mixed_instances(self):
        self.assertEqual(self.by_id['drew']['canonicalGender'], '?')
        self.assertEqual(self.by_id['silker']['canonicalGender'], 'M')
        self.assertEqual(self.by_id['cat']['canonicalGender'], 'mixed')
        self.assertEqual(self.by_id['cat']['ruAgreement'], 'neutral')
        self.assertEqual(self.by_id['veggie-kids']['ruAgreement'], 'resolve')
        self.assertEqual(self.by_id['veggie-eggplant']['canonicalGender'], 'M')
        self.assertEqual(self.by_id['veggie-potatogirl']['canonicalGender'], 'F')

    def test_regional_override_does_not_erase_fact(self):
        self.assertEqual(self.by_id['humphrey']['canonicalGender'], 'M')
        self.assertIn('humphrey', self.document['regionalNeutralIds'])
        self.assertIn('R001', self.by_id['humphrey']['note'])
        self.assertTrue(any('Visiting party/other regions excluded' in s for s in self.document['rules']))

    def test_meaning_only_term_keeps_discovery_and_compact_warning(self):
        self.assertIn('mailbox', [r['id'] for r in w.search(w.glossary(w.ROOT), ['POOL NOODLE'])])
        self.assertIn('ПАЛКА ДЛЯ ПЛАВАНИЯ', self.by_id['mailbox']['note'])

    def test_unrecognized_character_fails_instead_of_guessing(self):
        e = {'id': 'unclassified-new-person', 'category': 'Character', 'meaning': 'A boy-shaped statue says hello.'}
        with self.assertRaisesRegex(ValueError, 'Unclassified canonical gender'):
            c.gender(e)
        e['meaning'] = 'Male; he/him. A speaking statue.'
        self.assertEqual(c.gender(e), 'M')

    def test_changed_derived_file_rejected_with_matching_positive_control(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / c.OUTPUT
            path.parent.mkdir(parents=True)
            with patch.object(c, 'build', return_value=self.document):
                path.write_bytes(c.serialize(self.document))
                self.assertEqual(w.compact_glossary(root)[0], self.document)
                changed = copy.deepcopy(self.document)
                changed['entries'][0][3] = 'F'
                path.write_bytes(c.serialize(changed))
                with self.assertRaisesRegex(ValueError, 'stale or changed'):
                    w.compact_glossary(root)

    def test_exact_limit_and_incomplete_output_rejection(self):
        result = w.select_briefs(self.document, self.rows, ['sunny'], 100000)
        size = len(json.dumps(result, ensure_ascii=False))
        self.assertEqual(w.select_briefs(self.document, self.rows, ['sunny'], size), result)
        with self.assertRaisesRegex(ValueError, 'Complete compact entries exceed'):
            w.select_briefs(self.document, self.rows, ['sunny'], size - 1)


if __name__ == '__main__':
    unittest.main()
