import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('site_manifest', Path(__file__).parents[1] / 'Scripts/write_site_locale_manifest.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SiteManifestTests(unittest.TestCase):
    def test_shared_objects_and_changed_object_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            objects = root / 'Payload/objects'
            objects.mkdir(parents=True)
            plain = b'translated game data'
            key = hashlib.sha256(plain).hexdigest()
            packed = gzip.compress(plain)
            (objects / key).write_bytes(packed)
            catalog = {'game': 'OMORI', 'objects': {key: {'bytes': len(packed), 'unpackedBytes': len(plain), 'sha256': hashlib.sha256(packed).hexdigest()}},
                       'locales': [{'code': 'locale-' + str(i), 'files': {'data/a.KEL': {'object': key, 'sha256': 'output-hash'}}} for i in range(27)]}
            raw = json.dumps(catalog).encode()
            (root / 'Payload/catalog.json').write_bytes(raw)
            (root / 'Payload/payload-receipt.json').write_text(json.dumps({'catalogSha256': hashlib.sha256(raw).hexdigest(), 'pendingLocales': []}))
            manifest = module.write_manifest(root, 'windows')
            self.assertEqual(len(manifest['locales']), 27)
            for code, entry in manifest['locales'].items():
                inventory = root / entry['requiredPaths'][1]
                self.assertEqual(hashlib.sha256(inventory.read_bytes()).hexdigest(), entry['inventorySha256'])
                self.assertEqual(json.loads(inventory.read_text())['files'], catalog['locales'][0]['files'])
            (root / 'vnrevival-locales.json').unlink()
            (objects / key).write_bytes(gzip.compress(b'changed'))
            with self.assertRaisesRegex(ValueError, 'changed locale object'):
                module.write_manifest(root, 'windows')
            self.assertFalse((root / 'vnrevival-locales.json').exists())


if __name__ == '__main__':
    unittest.main()
