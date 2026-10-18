"""Exercise value-preserving presentation without weakening native controls."""
import unittest
from source_text_syntax import compare_text_controls, signature


class RussianNumberPresentationTests(unittest.TestCase):
    def test_positive_grouping_and_decimal_controls(self):
        for original, target in [('238,900 miles', '238 900 миль'),
                                 ('2,500 CLAMS', '2\u00a0500 РАКУШЕК'),
                                 ('1,500 CLAMS', '1\u202f500 РАКУШЕК'),
                                 ('$20.00', '$20,00'), ('22.71%', '22,71%')]:
            compare_text_controls(original, target)
        compare_text_controls(r'\c[4]2,500\c[0] %1', r'\c[4]2 500\c[0] %1')

    def test_exact_values_precision_order_and_controls_rejected(self):
        for original, target in [('238,900', '238 901'), ('2,500', '2,5'),
                                 ('2,500', '250'), ('20.00', '20,0'),
                                 ('22.71 1.77', '1,77 22,71'),
                                 ('V1.0.8', 'V1,0,8'), ('8/14', '14/8'),
                                 (r'\c[4]2,500\c[0] %1', r'\c[5]2 500\c[0] %1'),
                                 (r'\v[2500]', r'\v[2 500]')]:
            with self.subTest(original=original, target=target):
                with self.assertRaisesRegex(ValueError, 'controls/numbers changed'):
                    compare_text_controls(original, target)

    def test_source_inventory_tokenization_unchanged(self):
        self.assertEqual(signature('2,500 22.71 V1.0.8'),
                         [('original-number', '2,500'), ('original-number', '22.71'),
                          ('original-number', '1.0.8')])


if __name__ == '__main__':
    unittest.main()
