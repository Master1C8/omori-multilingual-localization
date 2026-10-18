"""Check label binding at the actual sidecar/lookup boundary, not game rendering."""
import copy
import json
from pathlib import Path
import subprocess
import unittest

from display_mapping import mapping_row, validate_mapping_document
from authoring_keys import target_key
from source_prepare import sha


class DisplayMappingTests(unittest.TestCase):
    def setUp(self):
        self.unit = {'id': 'data/Actors.KEL#[1,"name"]', 'asset': 'data/Actors.KEL',
                     'path': [1, 'name'], 'source': 'OMORI',
                     'sourceValueSha256': sha(b'OMORI'), 'role': 'visible-display-mapping'}
        self.entry = {'target': 'ОМОРИ'}
        self.doc = {'schemaVersion': 1, 'siteLocale': 'ru', 'steamBuild': '8879120',
                    'corpusManifestRawSha256': 'pinned',
                    'entries': [mapping_row(self.unit, self.entry['target'])]}

    def check_doc(self, doc):
        return validate_mapping_document(doc, [(self.unit, self.entry)], 'pinned')

    def test_exact_positive_and_wrong_identity(self):
        self.check_doc(self.doc)
        for key, value in [('path', [2, 'name']), ('source', 'SUNNY'), ('target', 'САННИ')]:
            bad = copy.deepcopy(self.doc); bad['entries'][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact source/author'):
                self.check_doc(bad)

    def test_duplicate_missing_and_wrong_build(self):
        for entries in [[], self.doc['entries'] * 2]:
            bad = copy.deepcopy(self.doc); bad['entries'] = entries
            with self.assertRaisesRegex(ValueError, 'ID coverage'): self.check_doc(bad)
        bad = copy.deepcopy(self.doc); bad['steamBuild'] = 'another'
        with self.assertRaisesRegex(ValueError, 'input binding'): self.check_doc(bad)

    def test_explicit_author_mode_and_span_rejection(self):
        self.assertEqual(target_key(self.unit, 'display-path'), '[1,"name"]')
        with self.assertRaisesRegex(ValueError, 'different exact authoring'):
            target_key(self.unit, 'json-path')
        bad = dict(self.unit, spanUtf16=[0, 5])
        with self.assertRaisesRegex(ValueError, 'exact source literal binding'):
            mapping_row(bad, 'ОМОРИ')

    def test_actual_lookup_preserves_logic_custom_names_and_ambiguity(self):
        module = Path(__file__).resolve().parent.parent / 'runtime/ru-display-labels.js'
        program = '''
const assert = require('assert');
const api = require(process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const record = {name: 'OMORI', id: 1};
const labels = api.createDisplayLabels(rows);
assert.strictEqual(labels.lookup('data/Actors.KEL', [1, 'name'], record.name), 'ОМОРИ');
assert.strictEqual(record.name, 'OMORI');
assert.strictEqual(record.id, 1);
assert.strictEqual(labels.lookup('data/Classes.KEL', [1, 'name'], 'OMORI'), 'OMORI');
assert.strictEqual(labels.lookup('data/Actors.KEL', [2, 'name'], 'OMORI'), 'OMORI');
assert.strictEqual(labels.lookup('data/Actors.KEL', [1, 'name'], 'Омори'), 'Омори');
assert.strictEqual(labels.lookup('data/Actors.KEL', [1, 'name'], 'OWNER_NAME'), 'OWNER_NAME');
assert.throws(() => api.createDisplayLabels(rows.concat(rows)), /Duplicate display identity/);
'''
        subprocess.run(['node', '-e', program, str(module), json.dumps(self.doc['entries'])], check=True,
                       capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
