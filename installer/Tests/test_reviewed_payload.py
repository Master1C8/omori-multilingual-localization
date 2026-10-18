"""Regression: a one-locale payload must not discard other tested revisions."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('assembly', Path(__file__).parents[1] / 'Scripts/assemble_reviewed_payload.py')
assembly = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assembly)


class ReviewedPayloadTests(unittest.TestCase):
    def inputs(self, root):
        entries = []
        for index in range(27):
            folder = root / str(index)
            (folder / 'objects').mkdir(parents=True)
            raw = ('tested-revision-' + str(index)).encode()
            key = assembly.sha(raw)
            packed = gzip.compress(raw, mtime=0)
            (folder / 'objects' / key).write_bytes(packed)
            row = {'code': str(index), 'name': str(index), 'archiveSha256': assembly.sha(raw),
                   'reviewStatus': 'pending-full-review', 'files': {'data/System.KEL': {
                       'object': key, 'bytes': len(raw), 'sha256': key, 'iv': ''}}}
            catalog = {'schemaVersion': 1, 'game': 'OMORI', 'steamAppID': '1150690', 'sourceBuild': '8879120',
                       'version': '1.0.0', 'runtimeCode': 'en', 'format': 'gzip-plaintext-native-ctr-v1',
                       'locales': [row], 'objects': {key: {'sha256': assembly.sha(packed), 'bytes': len(packed),
                                                        'unpackedBytes': len(raw)}},
                       'originals': {'data/System.KEL': 'same-original'}}
            content = json.dumps(catalog).encode()
            (folder / 'catalog.json').write_bytes(content)
            entries.append({'locale': str(index), 'catalog': str(folder), 'catalogSha256': assembly.sha(content)})
        inputs = root / 'inputs.json'
        inputs.write_text(json.dumps({'entries': entries}))
        completion = root / 'completion.json'
        completion.write_text(json.dumps({'status': 'complete', 'locales': [e['locale'] for e in entries],
                                         'finalInputsSha256': assembly.sha(inputs.read_bytes())}))
        return inputs, completion

    def test_all_tested_revisions_survive_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, completion = self.inputs(root)
            assembly.assemble(inputs, completion, root / 'release')
            result = json.loads((root / 'release/catalog.json').read_text())
            self.assertEqual(len(result['locales']), 27)
            for index, row in enumerate(result['locales']):
                file = row['files']['data/System.KEL']
                actual = gzip.decompress((root / 'release/objects' / file['object']).read_bytes())
                self.assertEqual(actual, ('tested-revision-' + str(index)).encode())
                self.assertEqual(row['reviewStatus'], 'pending-full-review')

    def test_stale_locale_rejects_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, completion = self.inputs(root)
            (root / '26/catalog.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Reviewed catalog changed: 26'):
                assembly.assemble(inputs, completion, root / 'release')
            self.assertFalse((root / 'release').exists())


if __name__ == '__main__':
    unittest.main()
