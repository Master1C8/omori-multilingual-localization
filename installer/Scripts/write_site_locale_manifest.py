#!/usr/bin/env python3
"""Describe and verify the native installer's shared, deduplicated locale payload.

The site checks structural presence; this producer verifies every referenced
compressed object and its decompressed content before writing locale inventories.
Inventories are packaging evidence, not additional installer runtime inputs.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_manifest(resources, platform):
    payload = resources / 'Payload'
    raw = (payload / 'catalog.json').read_bytes()
    catalog = json.loads(raw)
    receipt = json.loads((payload / 'payload-receipt.json').read_text())
    if digest(raw) != receipt['catalogSha256'] or catalog['game'] != 'OMORI':
        raise ValueError('Payload catalog fingerprint differs')
    codes = [row['code'] for row in catalog['locales']]
    if len(codes) != 27 or len(set(codes)) != 27 or receipt['pendingLocales']:
        raise ValueError('Expected the complete 27-locale release')
    verified = set()
    inventories = {}
    for row in catalog['locales']:
        code = row['code']
        if not code or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in code):
            raise ValueError('Unsafe locale code')
        if not row['files']:
            raise ValueError('Empty locale')
        for file in row['files'].values():
            key = file['object']
            if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
                raise ValueError('Unsafe object key')
            if key not in verified:
                packed = (payload / 'objects' / key).read_bytes()
                metadata = catalog['objects'][key]
                plain = gzip.decompress(packed)
                if (len(packed) != metadata['bytes'] or digest(packed) != metadata['sha256']
                        or len(plain) != metadata['unpackedBytes'] or digest(plain) != key):
                    raise ValueError('Missing or changed locale object: ' + key)
                verified.add(key)
        inventories[code] = {'schemaVersion': 1, 'locale': code,
                             'catalogSha256': digest(raw), 'files': row['files']}
    manifest = {'schemaVersion': 1, 'gameSlug': 'omori', 'platform': platform,
                'catalogSha256': digest(raw), 'locales': {}}
    inventory_dir = resources / 'locale-inventory'
    inventory_dir.mkdir(exist_ok=True)
    for code, inventory in inventories.items():
        relative = 'locale-inventory/' + code + '.json'
        data = (json.dumps(inventory, sort_keys=True, separators=(',', ':')) + '\n').encode()
        (resources / relative).write_bytes(data)
        manifest['locales'][code] = {
            'requiredPaths': ['Payload/catalog.json', relative, 'Payload/objects/'],
            'inventorySha256': digest(data), 'fileCount': len(inventory['files'])}
    data = (json.dumps(manifest, indent=2) + '\n').encode()
    if len(data) > 256 * 1024:
        raise ValueError('Site manifest exceeds its bounded reader')
    (resources / 'vnrevival-locales.json').write_bytes(data)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resources', type=Path)
    parser.add_argument('platform', choices=['windows', 'macos'])
    args = parser.parse_args()
    result = write_manifest(args.resources, args.platform)
    print('Verified site locale inventories:', len(result['locales']))
