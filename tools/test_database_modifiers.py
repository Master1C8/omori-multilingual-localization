import unittest
from source_text_syntax import compare_text_controls
from database_modifiers import validate_description_modifiers


class ModifierTests(unittest.TestCase):
    def setUp(self):
        self.unit = {'id': 'description-fixture', 'asset': 'data/Armors.KEL',
                     'path': [31, 'description'], 'source': 'ATK +10, DEF -5'}

    def test_sign_and_stat_rejections_after_native_positive(self):
        positive = 'АТАКА +10, ЗАЩИТА -5'
        compare_text_controls(self.unit['source'], positive)
        validate_description_modifiers(self.unit, positive)
        for negative in ['АТАКА -10, ЗАЩИТА -5', 'ЗАЩИТА +10, АТАКА -5']:
            compare_text_controls(self.unit['source'], negative)
            with self.subTest(target=negative), self.assertRaisesRegex(ValueError, 'stat/amount/sign'):
                validate_description_modifiers(self.unit, negative)

    def test_whitespace_percent_and_both_directions(self):
        unit = dict(self.unit, source='ALL STATS + 1, SPEED -10%')
        validate_description_modifiers(unit, 'ВСЕ ХАРАКТЕРИСТИКИ +1, СКОРОСТЬ -10%')
        unit = dict(unit, source='ВСЕ ХАРАКТЕРИСТИКИ +1, СКОРОСТЬ -10%')
        validate_description_modifiers(unit, 'ALL STATS + 1, SPD -10%')
        with self.assertRaisesRegex(ValueError, 'stat/amount/sign'):
            validate_description_modifiers(unit, 'ALL STATS +1, SPD -10')


if __name__ == '__main__':
    unittest.main()
