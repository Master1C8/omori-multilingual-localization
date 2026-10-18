"""Real image-container/byte gates with synthetic artwork; no game/visual claim."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'multilingual/delivery'))
import image_resources as images


class ImageResourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.game = self.root / 'game'
        self.locale = self.root / 'translation/es/images'
        self.locale.mkdir(parents=True)
        self.key = bytes(range(16))
        self.source = self.png((20, 12), 'RGBA', (0, 0, 0, 0))
        self.target = self.png((20, 12), 'RGBA', (255, 255, 255, 0))
        self.original = images.encode(self.source, self.key)
        original = self.game / 'img/pictures/fixture.rpgmvp'
        original.parent.mkdir(parents=True)
        original.write_bytes(self.original)
        self.artifact = self.file('translation/es/images/target.png', self.target)
        self.media = [{'asset': 'img/pictures/fixture.rpgmvp', 'rawSha256': images.digest(self.original),
                       'size': [20, 12], 'mode': 'RGBA', 'format': 'PNG'}]
        self.inventory = [{'asset': self.media[0]['asset'], 'sourceSha256': self.media[0]['rawSha256'],
                           'classification': 'text-bearing', 'reason': 'Synthetic fixture classification.'}]
        self.plans = [{'asset': self.media[0]['asset'], 'sourceSha256': self.media[0]['rawSha256'],
                       'targetSha256': self.artifact['sha256'], 'artifact': self.artifact,
                       'decision': 'clean', 'disposition': 'localized-resource',
                       'reason': 'Synthetic image dimensions/encoding fixture; no wording.'}]
        self.manifest = self.doc(images.MEDIA, {'assets': self.media})
        ctx = patch.object(images, 'MEDIA_SHA', self.manifest['sha256'])
        ctx.start(); self.addCleanup(ctx.stop)
        self.packet = self.locale / 'packet.json'
        self.save()

    def png(self, size, mode, color):
        from PIL import Image
        out = io.BytesIO(); Image.new(mode, size, color).save(out, format='PNG')
        return out.getvalue()

    def file(self, name, raw):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'sha256': images.digest(raw)}

    def doc(self, name, value):
        return self.file(name, (json.dumps(value) + '\n').encode())

    def save(self):
        inventory = self.doc('translation/es/images/inventory.json', self.inventory)
        plans = self.doc('translation/es/images/plans.json', self.plans)
        self.doc('translation/es/images/packet.json', {'sourceManifest': self.manifest,
                  'inventory': inventory, 'plans': plans})

    def load(self):
        return images.load(self.root, 'es', self.packet, self.game, self.key)

    def test_actual_encoded_resource_and_pinned_inputs(self):
        payload, rows, pins = self.load()
        self.assertEqual(images.decode(payload['files/' + self.media[0]['asset']], self.key), self.target)
        self.assertEqual(rows[0]['plaintextSha256'], images.digest(self.target))
        self.assertEqual(rows[0]['encoding'], 'rpgmv-image')
        self.assertEqual(pins['packet']['sha256'], images.digest(self.packet.read_bytes()))

    def test_codec_exact_header_and_independent_xor_control(self):
        expected = images.HEADER + bytes(v ^ self.key[i] if i < 16 else v for i, v in enumerate(self.target))
        self.assertEqual(images.encode(self.target, self.key), expected)
        self.assertEqual(images.decode(expected, self.key), self.target)
        with self.assertRaisesRegex(ValueError, 'header/key'):
            images.decode(b'bad-header' + expected[10:], self.key)

    def test_changed_original_rejected_after_matching_positive_control(self):
        self.load()
        path = self.game / self.media[0]['asset']; path.write_bytes(self.original + b'changed')
        with self.assertRaisesRegex(ValueError, 'Original game image changed'):
            self.load()

    def test_target_hash_and_same_locale_ownership(self):
        self.load()
        self.plans[0]['artifact'] = self.file('translation/fr/target.png', self.target)
        self.save()
        with self.assertRaisesRegex(ValueError, 'outside selected locale'):
            self.load()

    def test_dimensions_and_alpha_are_not_silently_replaced(self):
        self.load()
        for target, message in [(self.png((21, 12), 'RGBA', (0, 0, 0, 0)), 'dimensions/format'),
                                (self.png((20, 12), 'RGB', (0, 0, 0)), 'lost alpha')]:
            self.plans[0]['artifact'] = self.file('translation/es/images/target.png', target)
            self.plans[0]['targetSha256'] = images.digest(target); self.save()
            with self.assertRaisesRegex(ValueError, message):
                self.load()

    def test_inventory_and_plan_coverage(self):
        self.load()
        self.inventory.append(dict(self.inventory[0])); self.save()
        with self.assertRaisesRegex(ValueError, 'classification coverage/order'):
            self.load()

    def test_intentional_retention_omits_original_from_distributable(self):
        self.plans[0].update(disposition='intentional-retention', artifact=self.file('translation/es/images/raw.rpgmvp', self.original),
                             targetSha256=images.digest(self.original)); self.save()
        payload, rows, pins = self.load()
        self.assertEqual((payload, rows), ({}, []))
        self.assertEqual(pins['resources'][0]['disposition'], 'intentional-retention')
        self.plans[0]['artifact'] = self.artifact; self.plans[0]['targetSha256'] = self.artifact['sha256']; self.save()
        with self.assertRaisesRegex(ValueError, 'retention changed original'):
            self.load()

    def test_changed_plan_artifact_is_rejected(self):
        self.load()
        (self.root / self.artifact['path']).write_bytes(self.target + b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed image input'):
            self.load()


if __name__ == '__main__':
    unittest.main()
