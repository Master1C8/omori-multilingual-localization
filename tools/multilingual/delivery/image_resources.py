"""Package reviewed locale image resources without altering their artwork/wording.

Only encoding, dimensions, format and exact input/output bindings are checked here.
This module never produces translated wording or grants visual/editorial acceptance.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath

from PIL import Image

MEDIA = 'source/media-8879120-02/manifest.json'
MEDIA_SHA = 'f41a3e16eee1dbf81ef697dbc8c3cacecb5f12e6d446f433d7be8ec507ddad91'
HEADER = bytes.fromhex('5250474d560000000003010000000000')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw, key):
    if len(raw) < 32 or raw[:16] != HEADER or len(key) != 16:
        raise ValueError('Invalid RPGMV image header/key')
    body = bytearray(raw[16:])
    for index in range(16):
        body[index] ^= key[index]
    return bytes(body)


def encode(raw, key):
    if len(raw) < 16 or len(key) != 16:
        raise ValueError('Invalid RPGMV image payload/key')
    body = bytearray(raw)
    for index in range(16):
        body[index] ^= key[index]
    return HEADER + bytes(body)


def reference(root, ref, locale, source=False):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('Image input requires exact path/sha256')
    name = ref['path']
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or '\\' in name:
        raise ValueError('Unsafe image input path')
    path = root / name
    bases = [root / 'translation' / locale, root / 'runtime/multilingual/locales' / locale,
             root / 'build' / locale, root / 'build/multilingual-delivery' / locale]
    if source:
        bases.append(root / 'source')
    if not any(path.resolve().is_relative_to(base.resolve()) for base in bases):
        raise ValueError('Image input outside selected locale/source')
    if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)):
        raise ValueError('Image input symlink forbidden')
    raw = path.read_bytes()
    if digest(raw) != ref['sha256']:
        raise ValueError('Changed image input: ' + name)
    return path, raw


def load(root, locale, document, game_root, key):
    """Read the existing accepted imageText packet and encode localized artifacts."""
    root, document, game_root = map(lambda p: Path(p).resolve(), (root, document, game_root))
    packet_ref = {'path': str(document.relative_to(root)), 'sha256': digest(document.read_bytes())}
    _, packet_raw = reference(root, packet_ref, locale)
    packet = json.loads(packet_raw)
    if packet.get('sourceManifest') != {'path': MEDIA, 'sha256': MEDIA_SHA}:
        raise ValueError('Image packet must bind the complete pinned media manifest')
    _, media_raw = reference(root, packet['sourceManifest'], locale, source=True)
    _, inventory_raw = reference(root, packet['inventory'], locale)
    _, plans_raw = reference(root, packet['plans'], locale)
    media, inventory, plans = json.loads(media_raw)['assets'], json.loads(inventory_raw), json.loads(plans_raw)
    if [r.get('asset') for r in inventory] != [r['asset'] for r in media]:
        raise ValueError('Image classification coverage/order mismatch')
    originals = {r['asset']: r for r in media}
    for row in inventory:
        if (row.get('sourceSha256') != originals[row['asset']]['rawSha256']
                or row.get('classification') not in {'text-bearing', 'no-text'} or not row.get('reason')):
            raise ValueError('Invalid image classification binding')
    if [r.get('asset') for r in plans] != [r['asset'] for r in inventory if r['classification'] == 'text-bearing']:
        raise ValueError('Image plan coverage/order mismatch')
    payload, rows, bindings = {}, [], []
    for plan in plans:
        asset = plan['asset']; original = originals[asset]; relative = PurePosixPath(asset)
        if relative.is_absolute() or '..' in relative.parts or '\\' in asset:
            raise ValueError('Unsafe native image destination')
        if plan.get('sourceSha256') != original['rawSha256'] or plan.get('decision') != 'clean' or not plan.get('reason'):
            raise ValueError('Image plan is not source-bound/accepted')
        _, target = reference(root, plan['artifact'], locale, source=plan.get('disposition') == 'intentional-retention')
        if digest(target) != plan.get('targetSha256'):
            raise ValueError('Image target differs from accepted plan')
        if plan.get('disposition') == 'intentional-retention':
            if digest(target) != original['rawSha256']:
                raise ValueError('Intentional retention changed original bytes')
            bindings.append({'asset': asset, 'sourceSha256': original['rawSha256'],
                             'targetSha256': digest(target), 'disposition': 'intentional-retention'})
            continue
        if plan.get('disposition') != 'localized-resource':
            raise ValueError('Unknown image plan disposition')
        if Path(asset).suffix.lower() not in {'.rpgmvp', '.png', '.jpg', '.jpeg'}:
            raise ValueError('Localized media requires a supported image codec: ' + asset)
        original_raw = (game_root / asset).read_bytes()
        if digest(original_raw) != original['rawSha256']:
            raise ValueError('Original game image changed: ' + asset)
        plain = decode(target, key) if target.startswith(HEADER) else target
        with Image.open(io.BytesIO(plain)) as image:
            image.load()
            if list(image.size) != original.get('size') or image.format != original.get('format'):
                raise ValueError('Localized image dimensions/format differ: ' + asset)
            if original.get('mode') == 'RGBA' and image.mode != 'RGBA':
                raise ValueError('Localized image lost alpha channel: ' + asset)
        encrypted = asset.endswith('.rpgmvp')
        raw = encode(plain, key) if encrypted else plain
        if encrypted and decode(raw, key) != plain:
            raise ValueError('Image codec roundtrip failed')
        payload['files/' + asset] = raw
        rows.append({'path': asset, 'sha256': digest(raw), 'plaintextSha256': digest(plain),
                     'bytes': len(raw), 'encrypted': encrypted,
                     'encoding': 'rpgmv-image' if encrypted else 'plain-image'})
        bindings.append({'asset': asset, 'sourceSha256': original['rawSha256'],
                         'targetSha256': digest(target), 'artifact': plan['artifact'],
                         'disposition': 'localized-resource'})
    pins = {'packet': packet_ref, 'sourceManifest': packet['sourceManifest'],
            'inventory': packet['inventory'], 'plans': packet['plans'], 'resources': bindings}
    return payload, rows, pins
