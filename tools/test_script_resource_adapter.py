"""Literal/parent boundaries. These tests parse scripts without running the game."""
import json
import tempfile
import unittest
from pathlib import Path
from script_resource_adapter import (parsed_literals, program_edit, verify_program,
    build_resources, verify_resources, programs, original_resource, recover_program)
from text_resource_adapter import splice

ROOT = Path(__file__).resolve().parent.parent


class ScriptResources(unittest.TestCase):
    def pair(self, source, target, *, mapped=False):
        node = next(iter(parsed_literals(ROOT, 'fixture.js', source).values()))
        node['role'] = 'visible-display-mapping' if mapped else 'visible'
        return node, {'id': node['id'], 'source': node['source'], 'target': target}

    def test_literal_encoding_and_ast_value(self):
        original = 'const before = 2; const value = "😀test"; const after = true;'
        pair = self.pair(original, 'Ёж "здесь"\\\n😀')
        delivered = splice(original, [program_edit(*pair, ())], utf16=True)
        self.assertEqual(verify_program(ROOT, 'fixture.js', original, delivered, [pair])[pair[0]['id']], pair[1]['target'])
        self.assertTrue(delivered.startswith('const before = 2;'))
        self.assertTrue(delivered.endswith('const after = true;'))
        with self.assertRaisesRegex(ValueError, 'exact literal assembly'):
            verify_program(ROOT, 'fixture.js', original, delivered.replace('before = 2', 'before = 3'), [pair])
        changed = dict(pair[0], spanUtf16=[pair[0]['spanUtf16'][0] + 1, pair[0]['spanUtf16'][1]])
        with self.assertRaisesRegex(ValueError, 'Pinned original span'):
            splice(original, [program_edit(changed, pair[1], ())], utf16=True)

    def test_template_escape_value(self):
        original = 'const value = `hello`;'
        pair = self.pair(original, 'Привет `${имя}\\\n')
        delivered = splice(original, [program_edit(*pair, ())], utf16=True)
        self.assertEqual(verify_program(ROOT, 'fixture.js', original, delivered, [pair])[pair[0]['id']], pair[1]['target'])

    def test_mapping_and_retained_technical_literal_are_byte_exact(self):
        original = "const value = 'afraid';"
        pair = self.pair(original, 'НАПУГАН', mapped=True)
        self.assertEqual(splice(original, [program_edit(*pair, ())], utf16=True), original)
        self.assertEqual(verify_program(ROOT, 'fixture.js', original, original, [pair])[pair[0]['id']], 'afraid')
        pair = self.pair(original, 'afraid')
        self.assertEqual(splice(original, [program_edit(*pair, ())], utf16=True), original)

    def test_actual_embedded_note_parent_and_delivery(self):
        units = json.loads((ROOT / 'source/text-corpus-8879120-02/units.json').read_text())
        unit = next(u for u in units if u['asset'] == 'data/Skills.KEL#[758,"note"]@note:24')
        pair = unit, {'id': unit['id'], 'source': unit['source'], 'target': ': кража '}
        record = programs(ROOT)[unit['asset']]
        _, original = original_resource(ROOT, record['originalAsset'])
        recover_program(record, original)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            resources = build_resources(ROOT, out, [pair], ())
            self.assertEqual(verify_resources(ROOT, out / 'receipt.json', resources, [pair], ())[unit['id']], ': кража ')
        changed = json.loads(json.dumps(original))
        changed[758]['note'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'parent changed'):
            recover_program(record, changed)

    def test_actual_plugin_config_macro(self):
        units = json.loads((ROOT / 'source/text-corpus-8879120-02/units.json').read_text())
        unit = next(u for u in units if u['id'] == 'js/plugins.js#[100,"parameters","Macro 5 Text"]@macro:3')
        pair = unit, {'id': unit['id'], 'source': unit['source'], 'target': 'БЭЗИЛ'}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            resources = build_resources(ROOT, out, [pair], ())
            self.assertEqual(verify_resources(ROOT, out / 'receipt.json', resources, [pair], ())[unit['id']], 'БЭЗИЛ')


if __name__ == '__main__':
    unittest.main()
