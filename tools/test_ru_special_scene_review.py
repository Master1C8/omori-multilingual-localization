"""Known effect regressions and actual case-read graph guards; no game launch."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from ru_special_scene_review import check_contracts, verify_review, POEM, BOTTLES, BED_DEFINITIONS
from ru_static_inputs import current_inputs

ROOT = Path(__file__).resolve().parents[1]


class SpecialSceneReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = {entry['id']: entry['target']
                       for path in (ROOT/'translation/ru/batches').glob('*.json')
                       for entry in json.loads(path.read_text())['entries']}
        cls.proof = current_inputs(ROOT)['caseReview']

    def test_actual_repaired_group_positive(self):
        check_contracts(self.targets)
        self.assertEqual(len(verify_review(ROOT, self.proof)['reviewedIds']), 829)

    def test_rhyming_verse_with_unchanged_reaction_rejects(self):
        targets = dict(self.targets)
        targets[POEM] = targets[POEM].replace('Может, немного грустит...\nНо точно не мёртвый.',
                                            'Может, слегка грустит...\nНо вечным сном не спит.')
        self.assertIn('Тут даже рифмы нет', targets[POEM])
        with self.assertRaisesRegex(ValueError, 'SP008: known rhyming verse'):
            check_contracts(targets)

    def test_opaque_song_with_valid_blank_and_frame_rejects(self):
        targets = dict(self.targets)
        targets[BOTTLES[0]] = targets[BOTTLES[0]].replace(' — почти как «аморе»!', '.')
        self.assertIn('________', targets[BOTTLES[0]])
        self.assertIn('<br>', targets[BOTTLES[0]])
        with self.assertRaisesRegex(ValueError, 'SP016: name/song phonetic cue missing'):
            check_contracts(targets)

    def test_only_one_bottle_changed_rejects(self):
        targets = dict(self.targets)
        targets[BOTTLES[1]] = targets[BOTTLES[1]].replace('большая пицца', 'огромная пицца')
        with self.assertRaisesRegex(ValueError, 'SP016: bottle variants diverge'):
            check_contracts(targets)

    def test_device_without_bed_link_rejects(self):
        targets = dict(self.targets)
        targets[BED_DEFINITIONS[0]] = 'Также известен как УЛУЧШЕННЫЙ УНИЧТОЖИТЕЛЬ <br>\nУСТАЛОСТИ. B.E.D.'
        with self.assertRaisesRegex(ValueError, 'SP018: approved name/ordinary-bed link missing'):
            check_contracts(targets)

    def test_read_flags_do_not_override_stale_authors_or_missing_coverage(self):
        original = json.loads(self.proof.read_text())
        with tempfile.TemporaryDirectory(prefix='case-proof-', dir=ROOT/'build/ru') as temporary:
            path = Path(temporary)/'review.json'
            for field, reason in [('authorDependencies', 'reviewed author graph changed'),
                                  ('reviewedIds', 'reading coverage incomplete')]:
                damaged = copy.deepcopy(original)
                if field == 'authorDependencies':
                    damaged[field][next(iter(damaged[field]))] = '0'*64
                else:
                    damaged[field] = damaged[field][1:]
                path.write_text(json.dumps(damaged))
                with self.assertRaisesRegex(ValueError, reason):
                    verify_review(ROOT, path)

    def test_early_gender_with_unchanged_redactions_rejects(self):
        targets = dict(self.targets)
        identifier='languages/en/hidden_library.HERO#["message_70","text"]'
        targets[identifier]=targets[identifier].replace('повезло: досталась', 'повезло: ему досталась')
        self.assertEqual(targets[identifier].count('☐'),1)
        with self.assertRaisesRegex(ValueError,'SP013: premature redacted-participant gender marker'):
            check_contracts(targets)


if __name__ == '__main__':
    unittest.main()
