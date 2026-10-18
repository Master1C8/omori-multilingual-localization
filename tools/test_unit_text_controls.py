import unittest
from unit_text_controls import compare_unit_controls


class UnitControls(unittest.TestCase):
    def test_bound_ui_label_and_unrelated_html(self):
        unit = {'asset':'js/plugins.js', 'plugin':'YEP_EquipCore',
                'path':[29,'parameters','Empty Text'], 'role':'visible', 'source':'<Empty>'}
        compare_unit_controls(unit, '<Пусто>')
        for target in ['Пусто', '<Пусто', '<Пусто>\\n[8]', '<br>Пусто']:
            with self.assertRaises(ValueError): compare_unit_controls(unit, target)
        for change in [{'plugin':'Other'}, {'asset':'data/Items.KEL'}, {'source':'<br>'}]:
            with self.assertRaisesRegex(ValueError, 'Exact native text controls'):
                compare_unit_controls(dict(unit, **change), '<Пусто>')


if __name__ == '__main__': unittest.main()
