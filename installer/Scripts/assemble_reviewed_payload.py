#!/usr/bin/env python3
"""Assemble exact locale rows from pinned, completed native-QA inputs.

QA subcatalogs contain full, byte-identical locale rows. They must never be
used wholesale as a release: select each reviewed locale explicitly, merge
only its objects, and verify every reconstructed output and original hash.
This preserves existing editorial status; visual QA is not editorial approval.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = b'6bdb2e585882fbd48826ef9cffd4c511'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def assemble(inputs, completion, output):
    raw_inputs = inputs.read_bytes()
    done = load(completion)
    if done['status'] != 'complete' or sha(raw_inputs) != done['finalInputsSha256']:
        raise ValueError('Final QA input fingerprint or completion differs')
    entries = json.loads(raw_inputs)['entries']
    codes = [entry['locale'] for entry in entries]
    if len(codes) != len(set(codes)) or codes != done['locales'] or len(codes) != 27:
        raise ValueError('Expected the exact completed 27-locale set')
    if output.exists():
        raise ValueError('Preserve existing output; choose a fresh release directory')
    objects, originals, locales, sources, licenses = {}, {}, [], {}, {}
    common = None
    evidence = []
    for entry in entries:
        folder = Path(entry['catalog'])
        raw = (folder / 'catalog.json').read_bytes()
        if sha(raw) != entry['catalogSha256']:
            raise ValueError('Reviewed catalog changed: ' + entry['locale'])
        catalog = json.loads(raw)
        identity = {key: catalog[key] for key in ('schemaVersion', 'game', 'steamAppID',
                    'sourceBuild', 'version', 'runtimeCode', 'format')}
        if identity != (common or identity) or identity['game'] != 'OMORI' or identity['sourceBuild'] != '8879120':
            raise ValueError('Catalog identities differ')
        common = identity
        selected = [row for row in catalog['locales'] if row['code'] == entry['locale']]
        if len(selected) != 1:
            raise ValueError('Ambiguous locale row')
        row = selected[0]
        if len({name.casefold() for name in row['files']}) != len(row['files']):
            raise ValueError('Case-colliding resource paths')
        for name, file in row['files'].items():
            if any(part in ('', '.', '..') for part in name.split('/')) or '\\' in name or name.startswith('/'):
                raise ValueError('Unsafe resource path')
            key = file['object']
            metadata = catalog['objects'][key]
            if key in objects and metadata != objects[key]:
                raise ValueError('Conflicting compressed object')
            packed = (folder / 'objects' / key).read_bytes()
            plain = gzip.decompress(packed)
            if len(packed) != metadata['bytes'] or sha(packed) != metadata['sha256'] or len(plain) != metadata['unpackedBytes'] or sha(plain) != key:
                raise ValueError('Damaged object: ' + key)
            iv = base64.b64decode(file['iv'], validate=True)
            if iv:
                worker = Cipher(algorithms.AES(KEY), modes.CTR(iv)).encryptor()
                delivered = iv + worker.update(plain) + worker.finalize()
            else:
                delivered = plain
            if len(delivered) != file['bytes'] or sha(delivered) != file['sha256']:
                raise ValueError('Reconstructed resource differs: ' + name)
            objects[key] = metadata
            sources[key] = folder / 'objects' / key
            if name in catalog['originals']:
                original = catalog['originals'][name]
                if name in originals and originals[name] != original:
                    raise ValueError('Conflicting original resource: ' + name)
                originals[name] = original
            if name.startswith('fonts/') and name.endswith('.txt'):
                licenses[sha(delivered)] = delivered
        locales.append(row)
        evidence.append({'locale': row['code'], 'catalog': str(folder),
                         'catalogSha256': entry['catalogSha256'],
                         'archiveSha256': row['archiveSha256'], 'files': len(row['files'])})
    # All dependencies are verified before creating any output.
    output.mkdir(parents=True)
    (output / 'objects').mkdir()
    for key, source in sources.items():
        os.link(source, output / 'objects' / key)
    catalog = dict(common, locales=locales, objects=objects, originals=originals,
                   pendingLocales=[], runtimeQA='existing-pinned-native-QA; Windows rendering not-run')
    raw = (json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()
    (output / 'catalog.json').write_bytes(raw)
    (output / 'Licenses').mkdir()
    for key, license in licenses.items():
        (output / 'Licenses' / (key + '.txt')).write_bytes(license)
    receipt = {'catalogSha256': sha(raw), 'compressedBytes': sum(row['bytes'] for row in objects.values()),
               'objects': len(objects), 'locales': codes, 'pendingLocales': [],
               'verifiedDeliveredFiles': sum(len(row['files']) for row in locales),
               'sourceInputsSha256': sha(raw_inputs), 'completionSha256': sha(completion.read_bytes()),
               'sources': evidence, 'editorial': 'Existing locale reviewStatus preserved; no new editorial acceptance'}
    (output / 'payload-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--completion', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(args.inputs, args.completion, args.output), indent=2))
