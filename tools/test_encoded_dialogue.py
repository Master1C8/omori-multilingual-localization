"""Source-bound encoded-display regressions; no runtime or semantic-quality claim."""
import copy
import unittest
from pathlib import Path
from source_prepare import strict_json
from source_text_syntax import compare_text_controls
from encoded_dialogue import load_registry, authored_encoding, validate_entry, decode_display, decode_battle_display, BATTLE_CODEC


class EncodedDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent.parent
        cls.units = {u['id']:u for u in strict_json((cls.root / 'source/text-corpus-8879120-02/units.json').read_bytes())}
        cls.registry = load_registry(cls.root, cls.units)

    def setUp(self):
        self.unit = self.units[next(iter(self.registry))]
        text = 'Синтетическое сообщение для проверки кодека. ' * 4
        target, metadata = authored_encoding(self.unit, text, 'РОБОХАРТ', self.registry)
        self.entry = {'target':target,'encodedPayload':metadata}

    def check(self, entry):
        validate_entry(self.unit, entry, [], self.registry, 'РОБОХАРТ')

    def test_positive_actual_five_source_bindings_and_utf8_roundtrip(self):
        for key, row in self.registry.items():
            if row.get('codec') == BATTLE_CODEC:
                continue
            target, metadata = authored_encoding(self.units[key], self.entry['encodedPayload']['decodedTarget'], 'РОБОХАРТ', self.registry)
            validate_entry(self.units[key], {'target':target,'encodedPayload':metadata}, [], self.registry, 'РОБОХАРТ')
            decoded, blocks, _ = decode_display(target, 'РОБОХАРТ')
            self.assertEqual(decoded, metadata['decodedTarget'])
            self.assertEqual(len(blocks) - 1, row['lineBreakCount'])

    def test_all_four_battle_frames_utf8_and_internal_newline(self):
        rows = [row for row in self.registry.values() if row.get('codec') == BATTLE_CODEC]
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(self.registry), 9)
        for row in rows:
            text = 'Синтетическая строка для проверки.'
            if row['decodedEnglish'].endswith('\n'):
                text += '\n'
            target, metadata = authored_encoding(self.units[row['id']], text, 'РОБОХАРТ', self.registry)
            entry = {'target': target, 'encodedPayload': metadata}
            validate_entry(self.units[row['id']], entry, [], self.registry, 'РОБОХАРТ')
            decoded, _, skeleton = decode_battle_display(target, 'РОБОХАРТ')
            self.assertEqual(decoded, text)
            self.assertEqual(skeleton.count('<br>'), row['lineBreakCount'])
            bad = copy.deepcopy(entry)
            bad['target'] = bad['target'].replace('РОБОХАРТ', 'МОЛЛИ')
            with self.assertRaisesRegex(ValueError, 'Encoded battle prefix/frame changed'):
                validate_entry(self.units[row['id']], bad, [], self.registry, 'РОБОХАРТ')

    def test_battle_native_break_and_payload_corruption_are_rejected(self):
        row = next(row for row in self.registry.values() if row.get('codec') == BATTLE_CODEC and row['lineBreakCount'])
        unit = self.units[row['id']]
        target, metadata = authored_encoding(unit, 'Синтетическая строка.', 'РОБОХАРТ', self.registry)
        entry = {'target': target, 'encodedPayload': metadata}
        validate_entry(unit, entry, [], self.registry, 'РОБОХАРТ')
        bad = dict(entry, target=target.replace('<br>', ''))
        with self.assertRaisesRegex(ValueError, 'Exact native text controls/numbers changed'):
            validate_entry(unit, bad, [], self.registry, 'РОБОХАРТ')
        bad = dict(entry, target=target.replace('<br>', '<br>*'))
        with self.assertRaisesRegex(ValueError, 'Malformed battle Base64 payload'):
            validate_entry(unit, bad, [], self.registry, 'РОБОХАРТ')

    def test_battle_decoded_terminal_newline_cannot_disappear(self):
        row = next(row for row in self.registry.values() if row.get('codec') == BATTLE_CODEC and row['decodedEnglish'].endswith('\n'))
        unit = self.units[row['id']]
        target, metadata = authored_encoding(unit, 'Синтетическая строка.\n', 'РОБОХАРТ', self.registry)
        validate_entry(unit, {'target': target, 'encodedPayload': metadata}, [], self.registry, 'РОБОХАРТ')
        with self.assertRaisesRegex(ValueError, 'Decoded battle line breaks changed'):
            authored_encoding(unit, 'Синтетическая строка.', 'РОБОХАРТ', self.registry)

    def test_existing_five_delivered_payloads_remain_byte_identical(self):
        found = 0
        for path in (self.root / 'translation/ru/batches').glob('*.json'):
            for entry in strict_json(path.read_bytes())['entries']:
                metadata = entry.get('encodedPayload')
                if not metadata or metadata['codec'] == BATTLE_CODEC:
                    continue
                target, actual_metadata = authored_encoding(self.units[entry['id']], metadata['decodedTarget'], 'РОБОХАРТ', self.registry)
                self.assertEqual(target, entry['target'])
                self.assertEqual(actual_metadata, metadata)
                found += 1
        self.assertEqual(found, 5)

    def test_changed_incidental_payload_digits_allowed(self):
        with self.assertRaisesRegex(ValueError, 'Exact native text controls/numbers changed'):
            compare_text_controls(self.unit['source'], self.entry['target'])
        self.check(self.entry)

    def test_reject_malformed_payload_after_positive_control(self):
        self.check(self.entry)
        bad = copy.deepcopy(self.entry);bad['target'] = '*' + bad['target'][1:]
        with self.assertRaisesRegex(ValueError, 'Malformed Base64 payload'):
            self.check(bad)

    def test_reject_valid_payload_with_wrong_decoded_author_text(self):
        self.check(self.entry)
        bad = copy.deepcopy(self.entry);bad['encodedPayload']['decodedTarget'] += '!'
        with self.assertRaisesRegex(ValueError, 'Decoded delivered target differs'):
            self.check(bad)

    def test_reject_line_break_change_after_same_decoded_meaning(self):
        self.check(self.entry)
        bad = copy.deepcopy(self.entry);bad['target'] = bad['target'].replace('<br>', '', 1)
        with self.assertRaisesRegex(ValueError, 'Exact native text controls/numbers changed'):
            self.check(bad)

    def test_reject_changed_native_namebox(self):
        self.check(self.entry)
        bad = copy.deepcopy(self.entry);bad['target'] = bad['target'].replace('РОБОХАРТ', 'МОЛЛИ')
        with self.assertRaisesRegex(ValueError, 'Encoded native namebox changed'):
            self.check(bad)

    def test_reject_discovery_source_binding_change(self):
        units = dict(self.units);units[self.unit['id']] = dict(self.unit, source='changed')
        with self.assertRaisesRegex(ValueError, 'Encoded source binding changed'):
            load_registry(self.root, units)

    def test_normal_numeric_protection_and_no_codec_bypass(self):
        unit = {'id':'unencoded-fixture','source':'Value 10\\!'}
        validate_entry(unit, {'target':'Значение 10\\!'}, [], self.registry, 'РОБОХАРТ')
        with self.assertRaisesRegex(ValueError, 'Exact native text controls/numbers changed'):
            validate_entry(unit, {'target':'Значение 11\\!'}, [], self.registry, 'РОБОХАРТ')
        with self.assertRaisesRegex(ValueError, 'Encoded codec not authorized'):
            validate_entry(unit, {'target':'Значение 11\\!','encodedPayload':self.entry['encodedPayload']}, [], self.registry, 'РОБОХАРТ')

    def test_reject_missing_author_metadata(self):
        with self.assertRaisesRegex(ValueError, 'Encoded author metadata required'):
            self.check({'target':self.entry['target']})


if __name__ == '__main__':
    unittest.main()
